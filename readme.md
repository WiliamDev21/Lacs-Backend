# LACS Backend API

Sistema backend desarrollado con FastAPI para la gestión de usuarios, ubicaciones y autenticación JWT. Incluye un sistema completo de códigos postales de México con más de 156,000 registros.

## 🚀 Características Principales

- **Autenticación JWT** con roles diferenciados (Usuario/Admin)
- **Gestión completa de usuarios** con diferentes niveles de permisos
- **Base de datos de códigos postales mexicanos** (156,778 registros)
- **API RESTful** con documentación automática
- **Arquitectura basada en microservicios** con Docker
- **Base de datos MongoDB** con operaciones asíncronas
- **Sistema de generación automática de credenciales**

## 🏗️ Arquitectura

```
LACS-Backend/
├── BackendFastAPI/
│   ├── main.py                 # Punto de entrada de la aplicación
│   ├── requirements.txt        # Dependencias Python
│   ├── Dockerfile             # Configuración Docker
│   ├── CPdescarga.xml         # Base de datos XML de códigos postales
│   ├── config/                # Configuraciones
│   ├── docs/                  # Documentación adicional
│   ├── models/                # Modelos Pydantic
│   │   ├── admin_model.py
│   │   ├── user_model.py
│   │   ├── ubicacion_model.py
│   │   └── ...
│   ├── routers/               # Endpoints de la API
│   │   ├── auth_endpoint.py
│   │   ├── user_endpoint.py
│   │   ├── admin_endpoint.py
│   │   ├── ubicaciones_endpoint.py
│   │   └── router.py
│   ├── services/              # Servicios de negocio
│   │   ├── database.py
│   │   ├── jwt_service.py
│   │   └── load_ubicaciones.py
│   ├── utils/                 # Utilidades
│   │   └── credential_generator.py
│   └── tests/                 # Pruebas unitarias
├── docker-compose.yml         # Orquestación de contenedores
└── README.md                  # Este archivo
```

## 🛠️ Tecnologías Utilizadas

- **FastAPI** - Framework web moderno y rápido
- **MongoDB** - Base de datos NoSQL con Motor (driver asíncrono)
- **JWT (PyJWT)** - Autenticación y autorización
- **Pydantic** - Validación de datos y serialización
- **Docker & Docker Compose** - Containerización y orquestación
- **Uvicorn** - Servidor ASGI de alta performance
- **Python 3.11+** - Lenguaje de programación

## 📋 Prerequisitos

- Docker y Docker Compose instalados
- Python 3.11+ (para desarrollo local)
- Git

## 🚀 Instalación y Configuración

### Método 1: Docker (Recomendado)

1. **Clonar el repositorio:**
```bash
git clone https://github.com/WiliamDev21/Lacs-Backend.git
cd Lacs-Backend
```

2. **Construir y ejecutar con Docker Compose:**
```bash
docker-compose up --build -d
```

3. **Verificar que los servicios estén funcionando:**
```bash
docker-compose ps
```

4. **Acceder a la API:**
- API: http://localhost:8080
- Documentación interactiva: http://localhost:8080/docs
- MongoDB: localhost:27017

### Método 2: Desarrollo Local

1. **Instalar dependencias:**
```bash
cd BackendFastAPI
pip install -r requirements.txt
```

2. **Configurar variables de entorno:**
```bash
export MONGO_URI=mongodb://localhost:27017
```

3. **Ejecutar la aplicación:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

## 🔧 Configuración

### Variables de Entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `MONGO_URI` | URI de conexión a MongoDB | `mongodb://localhost:27017` |

### Base de Datos

La aplicación utiliza MongoDB con las siguientes colecciones:

- **users** - Información de usuarios del sistema
- **admins** - Información de administradores
- **ubicaciones** - Códigos postales y ubicaciones de México

## 📚 Documentación de la API

### Endpoints Principales

#### Autenticación
- `POST /api/auth/login/user` - Login de usuarios
- `POST /api/auth/login/admin` - Login de administradores

#### Gestión de Usuarios
- `GET /api/users/` - Listar usuarios (con filtros y paginación)
- `POST /api/users/` - Crear nuevo usuario
- `PUT /api/users/{nickname}` - Actualizar usuario
- `DELETE /api/users/{nickname}` - Eliminar usuario
- `POST /api/users/change-password` - Cambiar contraseña
- `GET /api/users/me` - Información del usuario actual

#### Administración
- `POST /api/admin/create-user` - Crear usuario (admin)
- `GET /api/admin/search-users` - Buscar usuarios (admin)
- `POST /api/admin/change-user-password` - Cambiar contraseña de usuario
- `POST /api/admin/reset-user-password` - Resetear contraseña

#### Ubicaciones (Códigos Postales)
- `GET /api/ubicaciones/cp/{codigo_postal}` - Buscar por código postal
- `GET /api/ubicaciones/buscar/estado/{estado}` - Buscar por estado
- `POST /api/ubicaciones/load-streaming` - Cargar base de datos XML
- `GET /api/ubicaciones/status` - Estado de la base de datos

### Roles de Usuario

| Rol | Permisos |
|-----|----------|
| **Developer** | Acceso completo a todas las funciones |
| **Administrador** | Gestión completa de usuarios y sistema |
| **Inspector** | Acceso a consultas y gestión de usuarios |
| **Supervisor** | Gestión limitada de usuarios |
| **Operador** | Acceso a consultas básicas |
| **Empleado** | Acceso limitado a sus propios datos |

## 🔐 Seguridad

- **JWT Tokens** con expiración configurable
- **Hashing de contraseñas** con PBKDF2
- **Validación de roles** en todos los endpoints
- **CORS** configurado para múltiples orígenes
- **Validación de entrada** con Pydantic
- **Generación automática de credenciales** seguras

## 📊 Base de Datos de Códigos Postales

El sistema incluye una base de datos completa de códigos postales mexicanos:

- **156,778 registros** de códigos postales únicos
- **Información detallada** de estados, municipios, ciudades
- **Asentamientos** con tipos y zonas
- **Búsqueda optimizada** con índices MongoDB

### Cargar Base de Datos de Ubicaciones

```bash
# Método streaming (recomendado para archivos grandes)
curl -X POST "http://localhost:8080/api/ubicaciones/load-streaming?force_reload=true"

# Verificar estado
curl "http://localhost:8080/api/ubicaciones/status"
```

## 🧪 Testing

```bash
# Ejecutar tests
cd BackendFastAPI
pytest

# Tests específicos
pytest tests/test_user.py -v
```

## 📱 Integración con Flutter

### Ejemplo de Autenticación

```dart
Future<Map<String, dynamic>> loginUser(String nickname, String password) async {
  final response = await http.post(
    Uri.parse('http://tu-servidor:8080/api/auth/login/user'),
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: {
      'username': nickname,
      'password': password,
    },
  );
  
  if (response.statusCode == 200) {
    final data = json.decode(response.body);
    // Guardar token: data['access_token']
    return data;
  }
  throw Exception('Error en login');
}
```

### Ejemplo de Búsqueda de Código Postal

```dart
Future<Map<String, dynamic>> buscarCodigoPostal(String cp) async {
  final response = await http.get(
    Uri.parse('http://tu-servidor:8080/api/ubicaciones/cp/$cp'),
  );
  
  if (response.statusCode == 200) {
    return json.decode(response.body);
  }
  throw Exception('Código postal no encontrado');
}
```

## 🔄 Comandos Útiles

### Docker

```bash
# Ver logs
docker-compose logs -f fastapi

# Reiniciar servicios
docker-compose restart

# Acceder al contenedor
docker-compose exec fastapi bash

# Parar servicios
docker-compose down
```

### Base de Datos

```bash
# Acceder a MongoDB
docker-compose exec mongo mongo

# Backup de base de datos
docker-compose exec mongo mongodump --out /data/backup

# Restaurar base de datos
docker-compose exec mongo mongorestore /data/backup
```

## 🐛 Troubleshooting

### Problemas Comunes

#### Error: "Archivo XML no encontrado"
```bash
# Verificar ubicación del archivo
curl "http://localhost:8080/api/ubicaciones/debug/file-location"

# Copiar archivo al contenedor
docker cp CPdescarga.xml lacs-backend_fastapi_1:/app/CPdescarga.xml
```

#### Error: "operation cancelled" en carga masiva
- Usar el endpoint `/load-streaming` en lugar de `/load-sync`
- El archivo XML es muy grande, usar procesamiento por lotes

#### Error de conexión a MongoDB
```bash
# Verificar que MongoDB esté corriendo
docker-compose ps mongo

# Revisar logs de MongoDB
docker-compose logs mongo
```

## 📈 Performance

### Optimizaciones Implementadas

- **Conexiones asíncronas** con Motor
- **Pooling de conexiones** MongoDB (50 conexiones)
- **Índices optimizados** para búsquedas rápidas
- **Paginación** en listados
- **Carga streaming** para archivos grandes
- **Background tasks** para operaciones pesadas

### Métricas Esperadas

- **Tiempo de respuesta**: < 200ms para consultas simples
- **Códigos postales**: Búsqueda en < 50ms
- **Autenticación**: < 100ms
- **Carga XML completa**: ~10-15 minutos (156K registros)

## 🤝 Contribución

1. Fork el proyecto
2. Crear una rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit los cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abrir un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 👨‍💻 Autor

**WiliamDev21**
- GitHub: [@WiliamDev21](https://github.com/WiliamDev21)

---

**Versión:** 1.0.0  
**Última actualización:** Julio 2025
