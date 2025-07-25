# Endpoints de Ubicaciones

Este módulo proporciona endpoints para cargar y consultar información de códigos postales, municipios, estados y asentamientos de México.

## Endpoints Disponibles

### 1. Verificar Estado de Carga
```
GET /api/ubicaciones/status
```
Verifica si las ubicaciones ya están cargadas en la base de datos.

**Respuesta:**
```json
{
  "status": "loaded|empty",
  "message": "string",
  "total_codigos_postales": 0,
  "total_asentamientos": 0
}
```

### 2. Cargar Ubicaciones (Asíncrono)
```
POST /api/ubicaciones/load?force_reload=false
```
Inicia la carga de ubicaciones en segundo plano desde el archivo XML.

**Parámetros:**
- `force_reload` (bool): Si es true, recarga los datos aunque ya existan

**Respuesta:**
```json
{
  "status": "loading|already_loaded",
  "message": "string",
  "task_started": true
}
```

### 3. Cargar Ubicaciones (Síncrono)
```
POST /api/ubicaciones/load-sync?force_reload=false
```
Carga ubicaciones síncronamente (espera a que termine). Recomendado solo para testing.

### 4. Buscar por Código Postal
```
GET /api/ubicaciones/{codigo_postal}
```
Obtiene información completa de un código postal específico.

**Ejemplo:**
```
GET /api/ubicaciones/01010
```

**Respuesta:**
```json
{
  "codigo_postal": "01010",
  "municipio": "Álvaro Obregón",
  "estado": "Ciudad de México",
  "ciudad": "Ciudad de México",
  "cp_oficina": "01001",
  "codigo_estado": "09",
  "codigo_oficina": "01001",
  "codigo_cp": "",
  "codigo_municipio": "010",
  "codigo_ciudad": "01",
  "asentamientos": [
    {
      "nombre": "Los Alpes",
      "tipo": "Colonia",
      "zona": "Urbano",
      "codigo_tipo": "09",
      "id_asentamiento": "0005"
    }
  ]
}
```

### 5. Buscar por Estado
```
GET /api/ubicaciones/buscar/estado/{estado}?limit=50&skip=0
```
Obtiene códigos postales filtrados por estado con paginación.

**Parámetros:**
- `estado` (string): Nombre del estado
- `limit` (int): Número máximo de resultados (default: 50, max: 100)
- `skip` (int): Número de resultados a omitir para paginación

**Ejemplo:**
```
GET /api/ubicaciones/buscar/estado/Ciudad de México?limit=10
```

## Estructura de Datos

Los datos se organizan por código postal, donde cada documento contiene:

- **Información geográfica**: estado, municipio, ciudad
- **Códigos oficiales**: códigos de estado, municipio, oficina
- **Asentamientos**: array con todos los asentamientos del código postal

## Flujo de Uso Recomendado

1. **Verificar estado**: `GET /ubicaciones/status`
2. **Si está vacío, cargar datos**: `POST /ubicaciones/load`
3. **Consultar ubicaciones**: `GET /ubicaciones/{codigo_postal}`

## Archivos Requeridos

El endpoint requiere que exista el archivo `CPdescarga.xml` en la raíz del proyecto con la estructura XML de códigos postales del Servicio Postal Mexicano.

## Notas Técnicas

- Los datos se cargan en lotes de 1000 registros
- Se crean índices automáticamente para optimizar búsquedas
- La búsqueda por código postal es única (clave primaria)
- Se agrupan múltiples asentamientos por código postal
- Manejo de errores robusto con mensajes descriptivos
