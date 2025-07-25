import xml.etree.ElementTree as ET
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = "lacs_db"
COLLECTION_NAME = "ubicaciones"

class UbicacionLoader:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
    
    async def connect_to_mongo(self):
        """Conectar a MongoDB"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URI)
            self.db = self.client[DATABASE_NAME]
            self.collection = self.db[COLLECTION_NAME]
            
            # Verificar conexión
            await self.client.admin.command('ping')
            print("✓ Conexión a MongoDB establecida")
            
        except Exception as e:
            print(f"✗ Error conectando a MongoDB: {e}")
            raise
    
    async def close_connection(self):
        """Cerrar conexión a MongoDB"""
        if self.client:
            self.client.close()
            print("✓ Conexión a MongoDB cerrada")
    
    def parse_xml_file(self, xml_file_path: str) -> List[Dict]:
        """
        Parsear archivo XML y extraer datos de ubicaciones agrupados por código postal
        
        Args:
            xml_file_path: Ruta al archivo XML
            
        Returns:
            Lista de diccionarios con los datos de ubicaciones agrupados por CP
        """
        cp_dict = {}  # Diccionario para agrupar por código postal
        
        try:
            # Parsear el archivo XML
            tree = ET.parse(xml_file_path)
            root = tree.getroot()
            
            # Buscar todos los elementos 'table' (cada uno representa una ubicación)
            tables = root.findall('.//table')
            
            print(f"✓ Encontrados {len(tables)} registros en el archivo XML")
            
            for table in tables:
                codigo_postal = self._get_element_text(table, 'd_codigo')
                
                # Solo procesar si tiene código postal válido
                if not codigo_postal:
                    continue
                
                # Crear estructura de asentamiento
                asentamiento = {
                    'nombre': self._get_element_text(table, 'd_asenta'),
                    'tipo': self._get_element_text(table, 'd_tipo_asenta'),
                    'zona': self._get_element_text(table, 'd_zona'),
                    'codigo_tipo': self._get_element_text(table, 'c_tipo_asenta'),
                    'id_asentamiento': self._get_element_text(table, 'id_asenta_cpcons')
                }
                
                # Si el CP no existe, crear nuevo registro
                if codigo_postal not in cp_dict:
                    cp_dict[codigo_postal] = {
                        'codigo_postal': codigo_postal,
                        'municipio': self._get_element_text(table, 'D_mnpio'),
                        'estado': self._get_element_text(table, 'd_estado'),
                        'ciudad': self._get_element_text(table, 'd_ciudad'),
                        'cp_oficina': self._get_element_text(table, 'd_CP'),
                        'codigo_estado': self._get_element_text(table, 'c_estado'),
                        'codigo_oficina': self._get_element_text(table, 'c_oficina'),
                        'codigo_cp': self._get_element_text(table, 'c_CP'),
                        'codigo_municipio': self._get_element_text(table, 'c_mnpio'),
                        'codigo_ciudad': self._get_element_text(table, 'c_cve_ciudad'),
                        'asentamientos': []
                    }
                
                # Agregar asentamiento solo si no está duplicado
                asentamientos_existentes = [a['nombre'] for a in cp_dict[codigo_postal]['asentamientos']]
                if asentamiento['nombre'] not in asentamientos_existentes:
                    cp_dict[codigo_postal]['asentamientos'].append(asentamiento)
            
            # Convertir diccionario a lista
            ubicaciones = list(cp_dict.values())
            
            # Estadísticas
            total_asentamientos = sum(len(ub['asentamientos']) for ub in ubicaciones)
            print(f"✓ Procesados {len(ubicaciones)} códigos postales únicos")
            print(f"✓ Total de asentamientos: {total_asentamientos}")
            
            return ubicaciones
            
        except ET.ParseError as e:
            print(f"✗ Error parseando XML: {e}")
            raise
        except FileNotFoundError:
            print(f"✗ Archivo no encontrado: {xml_file_path}")
            raise
        except Exception as e:
            print(f"✗ Error inesperado: {e}")
            raise
    
    def _get_element_text(self, parent, tag_name: str) -> str:
        """
        Obtener texto de un elemento hijo, manejo seguro de None
        
        Args:
            parent: Elemento padre
            tag_name: Nombre del tag hijo
            
        Returns:
            Texto del elemento o cadena vacía si no existe
        """
        element = parent.find(tag_name)
        return element.text.strip() if element is not None and element.text else ""
    
    async def insert_ubicaciones(self, ubicaciones: List[Dict], batch_size: int = 1000):
        """
        Insertar ubicaciones en MongoDB en lotes
        
        Args:
            ubicaciones: Lista de ubicaciones a insertar
            batch_size: Tamaño del lote para inserción
        """
        try:
            total = len(ubicaciones)
            inserted_count = 0
            
            # Limpiar colección existente (opcional)
            print("⚠ Limpiando colección existente...")
            await self.collection.delete_many({})
            
            # Insertar en lotes
            for i in range(0, total, batch_size):
                batch = ubicaciones[i:i + batch_size]
                result = await self.collection.insert_many(batch)
                inserted_count += len(result.inserted_ids)
                
                print(f"✓ Insertados {inserted_count}/{total} registros")
            
            print(f"✓ Proceso completado. Total insertado: {inserted_count} registros")
            
            # Crear índices para optimizar búsquedas
            await self._create_indexes()
            
        except Exception as e:
            print(f"✗ Error insertando en MongoDB: {e}")
            raise
    
    async def _create_indexes(self):
        """Crear índices para optimizar búsquedas"""
        try:
            # Índice único por código postal (campo principal de búsqueda)
            await self.collection.create_index("codigo_postal", unique=True)
            
            # Índice por estado y municipio
            await self.collection.create_index([("estado", 1), ("municipio", 1)])
            
            # Índice por nombre de asentamiento (dentro del array)
            await self.collection.create_index("asentamientos.nombre")
            
            # Índice por tipo de asentamiento
            await self.collection.create_index("asentamientos.tipo")
            
            # Índice compuesto para búsquedas geográficas
            await self.collection.create_index([("codigo_postal", 1), ("estado", 1), ("municipio", 1)])
            
            print("✓ Índices creados exitosamente")
            
        except Exception as e:
            print(f"⚠ Error creando índices: {e}")
    
    async def get_sample_data(self, limit: int = 5):
        """
        Obtener muestra de datos insertados para verificación
        
        Args:
            limit: Número de registros a mostrar
        """
        try:
            cursor = self.collection.find().limit(limit)
            documents = await cursor.to_list(length=limit)
            
            print(f"\n--- Muestra de {len(documents)} códigos postales ---")
            for i, doc in enumerate(documents, 1):
                print(f"\n{i}. CP: {doc.get('codigo_postal')}")
                print(f"   Municipio: {doc.get('municipio')}")
                print(f"   Estado: {doc.get('estado')}")
                print(f"   Ciudad: {doc.get('ciudad')}")
                
                asentamientos = doc.get('asentamientos', [])
                print(f"   Asentamientos ({len(asentamientos)}):")
                for j, asent in enumerate(asentamientos[:3], 1):  # Mostrar solo los primeros 3
                    print(f"     {j}. {asent.get('nombre')} ({asent.get('tipo')}) - {asent.get('zona')}")
                
                if len(asentamientos) > 3:
                    print(f"     ... y {len(asentamientos) - 3} más")
            
            # Estadísticas
            total_count = await self.collection.count_documents({})
            
            # Contar total de asentamientos
            pipeline = [
                {"$unwind": "$asentamientos"},
                {"$count": "total_asentamientos"}
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(1)
            total_asentamientos = result[0]['total_asentamientos'] if result else 0
            
            print(f"\n✓ Total de códigos postales: {total_count}")
            print(f"✓ Total de asentamientos: {total_asentamientos}")
            
        except Exception as e:
            print(f"✗ Error obteniendo muestra: {e}")
    
    async def buscar_por_codigo_postal(self, codigo_postal: str):
        """
        Ejemplo de búsqueda por código postal
        
        Args:
            codigo_postal: Código postal a buscar
        """
        try:
            documento = await self.collection.find_one({"codigo_postal": codigo_postal})
            
            if documento:
                print(f"\n--- Resultado para CP: {codigo_postal} ---")
                print(f"Municipio: {documento.get('municipio')}")
                print(f"Estado: {documento.get('estado')}")
                print(f"Ciudad: {documento.get('ciudad')}")
                
                asentamientos = documento.get('asentamientos', [])
                print(f"\nAsentamientos ({len(asentamientos)}):")
                for i, asent in enumerate(asentamientos, 1):
                    print(f"{i}. {asent.get('nombre')} ({asent.get('tipo')}) - {asent.get('zona')}")
            else:
                print(f"✗ No se encontró información para el CP: {codigo_postal}")
                
        except Exception as e:
            print(f"✗ Error en búsqueda: {e}")

async def main():
    """Función principal para ejecutar la carga de datos"""
    
    # Configuración
    XML_FILE_PATH = "../../CPdescarga.xml"  # Ruta al archivo XML en el directorio raíz
    
    loader = UbicacionLoader()
    
    try:
        print("=== Iniciando carga de ubicaciones ===\n")
        
        # 1. Conectar a MongoDB
        await loader.connect_to_mongo()
        
        # 2. Verificar que el archivo XML existe
        if not os.path.exists(XML_FILE_PATH):
            print(f"✗ Archivo XML no encontrado: {XML_FILE_PATH}")
            print("Por favor, coloca el archivo CPdescarga.xml en la ruta correcta")
            return
        
        # 3. Parsear archivo XML
        print(f"📁 Procesando archivo: {XML_FILE_PATH}")
        ubicaciones = loader.parse_xml_file(XML_FILE_PATH)
        
        if not ubicaciones:
            print("✗ No se encontraron ubicaciones válidas en el archivo")
            return
        
        # 4. Insertar en MongoDB
        print(f"\n💾 Insertando {len(ubicaciones)} ubicaciones en MongoDB...")
        await loader.insert_ubicaciones(ubicaciones)
        
        # 5. Mostrar muestra de datos
        await loader.get_sample_data()
        
        # 6. Ejemplo de búsqueda por código postal
        print("\n--- Ejemplo de búsqueda ---")
        await loader.buscar_por_codigo_postal("01010")  # Ejemplo con un CP común
        
        print("\n🎉 ¡Proceso completado exitosamente!")
        
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
    
    finally:
        # Cerrar conexión
        await loader.close_connection()

if __name__ == "__main__":
    asyncio.run(main())
