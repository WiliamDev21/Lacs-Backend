from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET
import os
from services.database import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase
from models.ubicacion_model import Ubicacion, Asentamiento

router = APIRouter(prefix="/ubicaciones", tags=["ubicaciones"])

# Modelos de respuesta
class LoadStatusResponse(BaseModel):
    status: str
    message: str
    total_codigos_postales: int
    total_asentamientos: int
    
class LoadResponse(BaseModel):
    status: str
    message: str
    task_started: bool = False

# Funciones auxiliares
def find_xml_file() -> str:
    """Buscar el archivo XML en múltiples ubicaciones posibles"""
    possible_paths = [
        # Ruta relativa desde el archivo actual (desarrollo)
        os.path.join(os.path.dirname(__file__), "../../CPdescarga.xml"),
        # Ruta desde la raíz del proyecto (Docker/producción)
        "/app/CPdescarga.xml",
        # Ruta desde el directorio actual
        "./CPdescarga.xml",
        # Ruta desde el directorio padre
        "../CPdescarga.xml",
        # Ruta absoluta común en Docker
        "/app/BackendFastAPI/CPdescarga.xml",
        # Ruta en el directorio de trabajo
        os.path.join(os.getcwd(), "CPdescarga.xml"),
        # Ruta en el directorio padre del directorio de trabajo
        os.path.join(os.path.dirname(os.getcwd()), "CPdescarga.xml")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Si no se encuentra, crear mensaje de error detallado
    error_msg = "Archivo XML no encontrado. Rutas verificadas:\n"
    for path in possible_paths:
        error_msg += f"  - {path} (existe: {os.path.exists(path)})\n"
    error_msg += f"\nDirectorio actual: {os.getcwd()}\n"
    error_msg += f"Directorio del script: {os.path.dirname(__file__)}\n"
    
    # Listar archivos en algunos directorios para debug
    try:
        current_files = os.listdir(os.getcwd())
        error_msg += f"Archivos en directorio actual: {current_files[:10]}...\n"
    except:
        pass
        
    try:
        parent_files = os.listdir(os.path.dirname(os.getcwd()))
        error_msg += f"Archivos en directorio padre: {parent_files[:10]}...\n"
    except:
        pass
    
    raise HTTPException(status_code=404, detail=error_msg)

def _get_element_text(parent, tag_name: str) -> str:
    """Obtener texto de un elemento hijo, manejo seguro de None"""
    # Intentar con namespace primero
    namespace = {'ns': 'NewDataSet'}
    element = parent.find(f'ns:{tag_name}', namespace)
    
    # Si no encuentra con namespace, intentar sin él
    if element is None:
        element = parent.find(tag_name)
    
    return element.text.strip() if element is not None and element.text else ""

def parse_xml_to_ubicaciones(xml_file_path: str) -> List[Dict]:
    """Parsear archivo XML y convertir a lista de ubicaciones agrupadas por CP"""
    cp_dict = {}
    
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # El XML tiene namespace, necesitamos buscarlo correctamente
        # Buscar elementos table tanto con namespace como sin él
        namespace = {'ns': 'NewDataSet'}
        tables = root.findall('.//ns:table', namespace)
        
        # Si no encuentra con namespace, intentar sin él
        if not tables:
            tables = root.findall('.//table')
        
        print(f"Encontradas {len(tables)} tablas en el XML")  # Debug
        
        for table in tables:
            codigo_postal_raw = _get_element_text(table, 'd_codigo')
            
            if not codigo_postal_raw:
                continue
            
            # Limpiar y validar código postal
            codigo_postal = codigo_postal_raw.strip()
            
            # Remover espacios y caracteres no numéricos
            codigo_postal = ''.join(filter(str.isdigit, codigo_postal))
            
            if not codigo_postal or len(codigo_postal) == 0:
                continue
            
            # Normalizar código postal a 5 dígitos
            codigo_postal = codigo_postal.zfill(5)
            
            # Crear estructura de asentamiento
            asentamiento = {
                'nombre': _get_element_text(table, 'd_asenta'),
                'tipo': _get_element_text(table, 'd_tipo_asenta'),
                'zona': _get_element_text(table, 'd_zona'),
                'codigo_tipo': _get_element_text(table, 'c_tipo_asenta'),
                'id_asentamiento': _get_element_text(table, 'id_asenta_cpcons')
            }
            
            # Si el CP no existe, crear nuevo registro
            if codigo_postal not in cp_dict:
                cp_dict[codigo_postal] = {
                    'codigo_postal': codigo_postal,
                    'municipio': _get_element_text(table, 'D_mnpio'),
                    'estado': _get_element_text(table, 'd_estado'),
                    'ciudad': _get_element_text(table, 'd_ciudad'),
                    'cp_oficina': _get_element_text(table, 'd_CP'),
                    'codigo_estado': _get_element_text(table, 'c_estado'),
                    'codigo_oficina': _get_element_text(table, 'c_oficina'),
                    'codigo_cp': _get_element_text(table, 'c_CP'),
                    'codigo_municipio': _get_element_text(table, 'c_mnpio'),
                    'codigo_ciudad': _get_element_text(table, 'c_cve_ciudad'),
                    'asentamientos': []
                }
            
            # Agregar asentamiento si no está duplicado
            asentamientos_existentes = [a['nombre'] for a in cp_dict[codigo_postal]['asentamientos']]
            if asentamiento['nombre'] not in asentamientos_existentes:
                cp_dict[codigo_postal]['asentamientos'].append(asentamiento)
        
        return list(cp_dict.values())
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parseando XML: {str(e)}")

async def load_ubicaciones_to_db(db: AsyncIOMotorDatabase) -> Dict:
    """Cargar ubicaciones desde XML a la base de datos"""
    collection = db.ubicaciones
    
    try:
        # Buscar archivo XML
        xml_file_path = find_xml_file()
        print(f"Archivo XML encontrado en: {xml_file_path}")  # Log para debug
        
        # Parsear XML
        ubicaciones = parse_xml_to_ubicaciones(xml_file_path)
        
        if not ubicaciones:
            raise HTTPException(
                status_code=400, 
                detail="No se encontraron ubicaciones válidas en el archivo XML"
            )
        
        print(f"Ubicaciones parseadas: {len(ubicaciones)}")  # Debug
        
        # Limpiar colección existente
        print("Limpiando colección existente...")
        await collection.delete_many({})
        
        # Insertar en lotes más pequeños con manejo de timeouts
        batch_size = 100  # Reducido de 1000 a 100
        total_inserted = 0
        total_batches = (len(ubicaciones) + batch_size - 1) // batch_size
        
        print(f"Insertando {len(ubicaciones)} ubicaciones en {total_batches} lotes de {batch_size}...")
        
        for i in range(0, len(ubicaciones), batch_size):
            batch = ubicaciones[i:i + batch_size]
            batch_number = (i // batch_size) + 1
            
            try:
                # Configurar timeout más largo para la operación
                result = await collection.insert_many(
                    batch, 
                    ordered=False,  # Continúa aunque falle un documento
                    bypass_document_validation=False
                )
                total_inserted += len(result.inserted_ids)
                
                # Log de progreso cada 10 lotes
                if batch_number % 10 == 0:
                    print(f"Procesado lote {batch_number}/{total_batches} - Insertados: {total_inserted}")
                    
            except Exception as batch_error:
                print(f"Error en lote {batch_number}: {str(batch_error)}")
                # Intentar insertar uno por uno si falla el lote
                for doc in batch:
                    try:
                        await collection.insert_one(doc)
                        total_inserted += 1
                    except Exception as doc_error:
                        print(f"Error insertando documento: {str(doc_error)[:100]}...")
                        continue
        
        print(f"Inserción completada. Total insertado: {total_inserted}")
        
        # Crear índices de forma asíncrona
        print("Creando índices...")
        try:
            # Crear índices uno por uno para evitar timeouts
            await collection.create_index("codigo_postal", unique=True, background=True)
            print("Índice de código postal creado")
            
            await collection.create_index([("estado", 1), ("municipio", 1)], background=True)
            print("Índice de estado-municipio creado")
            
            await collection.create_index("asentamientos.nombre", background=True)
            print("Índice de asentamientos creado")
            
        except Exception as index_error:
            print(f"Error creando índices: {str(index_error)}")
            # Los índices no son críticos, continuar sin ellos
        
        # Contar asentamientos totales con timeout
        print("Contando asentamientos...")
        try:
            pipeline = [
                {"$unwind": "$asentamientos"},
                {"$count": "total_asentamientos"}
            ]
            # Configurar timeout para la agregación
            result = await collection.aggregate(pipeline).to_list(1)
            total_asentamientos = result[0]['total_asentamientos'] if result else 0
        except Exception as count_error:
            print(f"Error contando asentamientos: {str(count_error)}")
            total_asentamientos = 0  # Usar 0 si falla el conteo
        
        return {
            "total_codigos_postales": total_inserted,
            "total_asentamientos": total_asentamientos,
            "message": "Ubicaciones cargadas exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error general cargando ubicaciones: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error cargando ubicaciones: {str(e)}")

# Endpoints
@router.get("/status", response_model=LoadStatusResponse, summary="Verificar estado de carga de ubicaciones")
async def get_load_status(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Verificar si las ubicaciones ya están cargadas en la base de datos
    """
    try:
        collection = db.ubicaciones
        
        # Contar documentos
        total_codigos_postales = await collection.count_documents({})
        
        if total_codigos_postales == 0:
            return LoadStatusResponse(
                status="empty",
                message="No hay ubicaciones cargadas en la base de datos",
                total_codigos_postales=0,
                total_asentamientos=0
            )
        
        # Contar asentamientos totales
        pipeline = [
            {"$unwind": "$asentamientos"},
            {"$count": "total_asentamientos"}
        ]
        result = await collection.aggregate(pipeline).to_list(1)
        total_asentamientos = result[0]['total_asentamientos'] if result else 0
        
        return LoadStatusResponse(
            status="loaded",
            message="Ubicaciones ya están cargadas",
            total_codigos_postales=total_codigos_postales,
            total_asentamientos=total_asentamientos
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verificando estado: {str(e)}")

@router.post("/load", response_model=LoadResponse, summary="Cargar ubicaciones desde XML")
async def load_ubicaciones(
    force_reload: bool = False,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Cargar ubicaciones desde el archivo XML a la base de datos.
    
    - **force_reload**: Si es True, recarga los datos aunque ya existan
    - La carga se ejecuta en segundo plano para archivos grandes
    """
    try:
        collection = db.ubicaciones
        
        # Verificar si ya existen datos
        existing_count = await collection.count_documents({})
        
        if existing_count > 0 and not force_reload:
            return LoadResponse(
                status="already_loaded",
                message=f"Ya existen {existing_count} códigos postales. Use force_reload=true para recargar."
            )
        
        # Ejecutar carga en segundo plano
        background_tasks.add_task(load_ubicaciones_to_db, db)
        
        return LoadResponse(
            status="loading",
            message="Carga de ubicaciones iniciada en segundo plano",
            task_started=True
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error iniciando carga: {str(e)}")

@router.post("/load-sync", response_model=LoadStatusResponse, summary="Cargar ubicaciones síncronamente")
async def load_ubicaciones_sync(
    force_reload: bool = False,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Cargar ubicaciones síncronamente (espera a que termine).
    Recomendado solo para testing o archivos pequeños.
    """
    try:
        collection = db.ubicaciones
        
        # Verificar si ya existen datos
        existing_count = await collection.count_documents({})
        
        if existing_count > 0 and not force_reload:
            # Contar asentamientos
            pipeline = [
                {"$unwind": "$asentamientos"},
                {"$count": "total_asentamientos"}
            ]
            result = await collection.aggregate(pipeline).to_list(1)
            total_asentamientos = result[0]['total_asentamientos'] if result else 0
            
            return LoadStatusResponse(
                status="already_loaded",
                message=f"Ya existen {existing_count} códigos postales",
                total_codigos_postales=existing_count,
                total_asentamientos=total_asentamientos
            )
        
        # Ejecutar carga síncronamente
        result = await load_ubicaciones_to_db(db)
        
        return LoadStatusResponse(
            status="loaded",
            message=result["message"],
            total_codigos_postales=result["total_codigos_postales"],
            total_asentamientos=result["total_asentamientos"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en carga síncrona: {str(e)}")

async def load_ubicaciones_streaming(db: AsyncIOMotorDatabase) -> Dict:
    """Cargar ubicaciones procesando el XML de forma streaming para evitar timeout"""
    collection = db.ubicaciones
    
    try:
        xml_file_path = find_xml_file()
        print(f"Iniciando carga streaming desde: {xml_file_path}")
        
        # Limpiar colección existente
        await collection.delete_many({})
        
        # Procesar XML de forma streaming
        cp_dict = {}
        batch = []
        batch_size = 50  # Lotes muy pequeños
        total_processed = 0
        total_inserted = 0
        
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # Buscar elementos table
        namespace = {'ns': 'NewDataSet'}
        tables = root.findall('.//ns:table', namespace)
        if not tables:
            tables = root.findall('.//table')
        
        print(f"Procesando {len(tables)} registros en modo streaming...")
        
        for idx, table in enumerate(tables):
            total_processed += 1
            
            codigo_postal_raw = _get_element_text(table, 'd_codigo')
            if not codigo_postal_raw:
                continue
            
            # Limpiar código postal
            codigo_postal = ''.join(filter(str.isdigit, codigo_postal_raw.strip()))
            if not codigo_postal:
                continue
            codigo_postal = codigo_postal.zfill(5)
            
            # Crear estructura de asentamiento
            asentamiento = {
                'nombre': _get_element_text(table, 'd_asenta'),
                'tipo': _get_element_text(table, 'd_tipo_asenta'),
                'zona': _get_element_text(table, 'd_zona'),
                'codigo_tipo': _get_element_text(table, 'c_tipo_asenta'),
                'id_asentamiento': _get_element_text(table, 'id_asenta_cpcons')
            }
            
            # Agregar al diccionario temporal
            if codigo_postal not in cp_dict:
                cp_dict[codigo_postal] = {
                    'codigo_postal': codigo_postal,
                    'municipio': _get_element_text(table, 'D_mnpio'),
                    'estado': _get_element_text(table, 'd_estado'),
                    'ciudad': _get_element_text(table, 'd_ciudad'),
                    'cp_oficina': _get_element_text(table, 'd_CP'),
                    'codigo_estado': _get_element_text(table, 'c_estado'),
                    'codigo_oficina': _get_element_text(table, 'c_oficina'),
                    'codigo_cp': _get_element_text(table, 'c_CP'),
                    'codigo_municipio': _get_element_text(table, 'c_mnpio'),
                    'codigo_ciudad': _get_element_text(table, 'c_cve_ciudad'),
                    'asentamientos': []
                }
            
            # Agregar asentamiento si no está duplicado
            asentamientos_existentes = [a['nombre'] for a in cp_dict[codigo_postal]['asentamientos']]
            if asentamiento['nombre'] not in asentamientos_existentes:
                cp_dict[codigo_postal]['asentamientos'].append(asentamiento)
            
            # Insertar en lotes pequeños frecuentemente
            if len(cp_dict) >= batch_size:
                batch = list(cp_dict.values())
                try:
                    result = await collection.insert_many(batch, ordered=False)
                    total_inserted += len(result.inserted_ids)
                    cp_dict.clear()  # Limpiar diccionario
                    
                    if total_inserted % 500 == 0:
                        print(f"Insertados {total_inserted} CPs, procesados {total_processed} registros")
                        
                except Exception as batch_error:
                    print(f"Error en lote streaming: {str(batch_error)}")
                    # Insertar uno por uno si falla
                    for doc in batch:
                        try:
                            await collection.insert_one(doc)
                            total_inserted += 1
                        except:
                            continue
                    cp_dict.clear()
        
        # Insertar último lote
        if cp_dict:
            batch = list(cp_dict.values())
            try:
                result = await collection.insert_many(batch, ordered=False)
                total_inserted += len(result.inserted_ids)
            except Exception as final_error:
                print(f"Error en lote final: {str(final_error)}")
                for doc in batch:
                    try:
                        await collection.insert_one(doc)
                        total_inserted += 1
                    except:
                        continue
        
        print(f"Carga streaming completada. Total insertado: {total_inserted}")
        
        # Crear índices de forma segura
        try:
            await collection.create_index("codigo_postal", unique=True, background=True)
            await collection.create_index([("estado", 1), ("municipio", 1)], background=True)
            await collection.create_index("asentamientos.nombre", background=True)
        except Exception as index_error:
            print(f"Advertencia - Error creando índices: {str(index_error)}")
        
        return {
            "total_codigos_postales": total_inserted,
            "total_asentamientos": 0,  # Se calculará después si es necesario
            "message": "Ubicaciones cargadas exitosamente con método streaming"
        }
        
    except Exception as e:
        print(f"Error en carga streaming: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en carga streaming: {str(e)}")

@router.post("/load-streaming", response_model=LoadStatusResponse, summary="Cargar ubicaciones con método streaming (recomendado)")
async def load_ubicaciones_streaming_endpoint(
    force_reload: bool = False,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Cargar ubicaciones usando método streaming optimizado para archivos grandes.
    Recomendado para evitar timeouts con archivos de muchos registros.
    """
    try:
        collection = db.ubicaciones
        
        # Verificar si ya existen datos
        existing_count = await collection.count_documents({})
        
        if existing_count > 0 and not force_reload:
            # Contar asentamientos
            try:
                pipeline = [
                    {"$unwind": "$asentamientos"},
                    {"$count": "total_asentamientos"}
                ]
                result = await collection.aggregate(pipeline).to_list(1)
                total_asentamientos = result[0]['total_asentamientos'] if result else 0
            except:
                total_asentamientos = 0
            
            return LoadStatusResponse(
                status="already_loaded",
                message=f"Ya existen {existing_count} códigos postales",
                total_codigos_postales=existing_count,
                total_asentamientos=total_asentamientos
            )
        
        # Ejecutar carga streaming
        result = await load_ubicaciones_streaming(db)
        
        return LoadStatusResponse(
            status="loaded",
            message=result["message"],
            total_codigos_postales=result["total_codigos_postales"],
            total_asentamientos=result["total_asentamientos"]
        )
        
    except HTTPException:
        raise

@router.get("/buscar/estado/{estado}", summary="Buscar códigos postales por estado")
async def get_ubicaciones_by_estado(
    estado: str,
    limit: int = 50,
    skip: int = 0,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Obtener códigos postales filtrados por estado.
    
    - **estado**: Nombre del estado
    - **limit**: Número máximo de resultados (default: 50, max: 100)
    - **skip**: Número de resultados a omitir para paginación
    """
    try:
        # Validar límites
        if limit > 100:
            limit = 100
        
        collection = db.ubicaciones
        
        # Búsqueda case-insensitive
        query = {"estado": {"$regex": estado, "$options": "i"}}
        
        cursor = collection.find(
            query, 
            {"_id": 0}  # Excluir _id
        ).skip(skip).limit(limit)
        
        ubicaciones = await cursor.to_list(length=limit)
        
        # Contar total de resultados
        total = await collection.count_documents(query)
        
        return {
            "ubicaciones": ubicaciones,
            "total": total,
            "limit": limit,
            "skip": skip,
            "has_more": skip + limit < total
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en búsqueda por estado: {str(e)}")

@router.get("/debug/sample", summary="Ver muestra de códigos postales (debug)")
async def get_sample_codigos_postales(
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Endpoint de debug para ver una muestra de códigos postales en la base de datos
    """
    try:
        collection = db.ubicaciones
        
        # Obtener muestra de códigos postales
        cursor = collection.find(
            {}, 
            {"codigo_postal": 1, "municipio": 1, "estado": 1, "_id": 0}
        ).limit(limit)
        
        ubicaciones = await cursor.to_list(length=limit)
        
        return {
            "sample_codigos_postales": ubicaciones,
            "total_count": await collection.count_documents({})
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo muestra: {str(e)}")

@router.get("/debug/file-location", summary="Verificar ubicación del archivo XML")
async def debug_file_location():
    """
    Endpoint de debug para verificar dónde se encuentra el archivo XML
    """
    try:
        # Intentar encontrar el archivo
        try:
            xml_file_path = find_xml_file()
            file_found = True
            file_size = os.path.getsize(xml_file_path)
        except HTTPException as e:
            xml_file_path = None
            file_found = False
            file_size = 0
            error_detail = str(e.detail)
        
        # Información del sistema
        return {
            "file_found": file_found,
            "file_path": xml_file_path,
            "file_size_bytes": file_size,
            "current_working_directory": os.getcwd(),
            "script_directory": os.path.dirname(__file__),
            "error_detail": error_detail if not file_found else None,
            "environment_info": {
                "python_executable": os.sys.executable,
                "platform": os.name
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verificando archivo: {str(e)}")

@router.get("/debug/xml-sample", summary="Ver muestra de datos raw del XML (debug)")
async def debug_xml_sample(limit: int = 5):
    """
    Endpoint de debug para ver datos raw del XML antes de procesar
    """
    try:
        # Buscar archivo XML
        xml_file_path = find_xml_file()
        
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # Buscar tables con namespace
        namespace = {'ns': 'NewDataSet'}
        tables = root.findall('.//ns:table', namespace)
        
        # Si no encuentra con namespace, intentar sin él
        if not tables:
            tables = root.findall('.//table')
        
        samples = []
        count = 0
        
        for table in tables:
            if count >= limit:
                break
                
            d_codigo_raw = _get_element_text(table, 'd_codigo')
            d_CP_raw = _get_element_text(table, 'd_CP')
            
            samples.append({
                "d_codigo_raw": repr(d_codigo_raw),  # usar repr para ver caracteres especiales
                "d_codigo_cleaned": ''.join(filter(str.isdigit, d_codigo_raw)) if d_codigo_raw else "",
                "d_CP_raw": repr(d_CP_raw),
                "municipio": _get_element_text(table, 'D_mnpio'),
                "estado": _get_element_text(table, 'd_estado'),
                "asentamiento": _get_element_text(table, 'd_asenta')
            })
            count += 1
        
        return {
            "xml_samples": samples,
            "total_tables_found": len(tables)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo XML: {str(e)}")

@router.get("/cp/{codigo_postal}", response_model=Optional[Ubicacion], summary="Buscar ubicación por código postal")
async def get_ubicacion_by_cp(
    codigo_postal: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Obtener información de ubicación por código postal.
    
    - **codigo_postal**: Código postal a buscar (5 dígitos)
    """
    try:
        collection = db.ubicaciones
        
        # Validar y limpiar el código postal
        codigo_postal_original = codigo_postal
        codigo_postal = codigo_postal.strip()
        
        # Remover espacios y caracteres no numéricos
        codigo_postal = ''.join(filter(str.isdigit, codigo_postal))
        
        if not codigo_postal:
            raise HTTPException(
                status_code=400, 
                detail=f"El código postal '{codigo_postal_original}' no contiene dígitos válidos"
            )
        
        # Normalizar a 5 dígitos agregando ceros a la izquierda
        codigo_postal = codigo_postal.zfill(5)
        
        if len(codigo_postal) > 5:
            raise HTTPException(
                status_code=400, 
                detail=f"El código postal '{codigo_postal_original}' tiene demasiados dígitos"
            )
        
        # Buscar por código postal
        ubicacion = await collection.find_one({"codigo_postal": codigo_postal})
        
        if not ubicacion:
            # Verificar si hay datos cargados
            total_count = await collection.count_documents({})
            if total_count == 0:
                raise HTTPException(
                    status_code=404, 
                    detail="No hay ubicaciones cargadas. Use /ubicaciones/load para cargar los datos."
                )
            else:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No se encontró información para el código postal {codigo_postal}"
                )
        
        # Remover el _id de MongoDB para la respuesta
        ubicacion.pop('_id', None)
        
        return Ubicacion(**ubicacion)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}")
