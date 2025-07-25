"""
Script de prueba para demostrar la generación automática de credenciales
"""
import requests
import json

BASE_URL = "http://localhost:8080"

def test_create_first_admin():
    """Crear el primer administrador del sistema"""
    print("=== Creando primer administrador ===")
    
    data = {
        "nombre": "Juan Carlos",
        "apellido_paterno": "García",
        "apellido_materno": "López"
    }
    
    response = requests.post(f"{BASE_URL}/api/admin/create-first-admin", data=data)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Primer administrador creado exitosamente")
        print(f"Nickname generado: {result['generated_credentials']['nickname']}")
        print(f"Password generado: {result['generated_credentials']['password']}")
        return result['generated_credentials']
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None

def test_create_user(admin_credentials):
    """Crear un usuario usando las credenciales del admin"""
    print("\n=== Creando usuario ===")
    
    data = {
        "admin_nickname": admin_credentials["nickname"],
        "admin_password": admin_credentials["password"],
        "nombre": "María Elena",
        "apellido_paterno": "Rodríguez",
        "apellido_materno": "Hernández",
        "email": "maria.rodriguez@acme.com",
        "telefono": "5551234567",
        "rol": "Empleado"
    }
    
    response = requests.post(f"{BASE_URL}/api/admin/create-user", data=data)
    
    if response.status_code == 201:
        result = response.json()
        print("✅ Usuario creado exitosamente")
        print(f"Nickname generado: {result['generated_credentials']['nickname']}")
        print(f"Password generado: {result['generated_credentials']['password']}")
        return result
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None

def main():
    print("🚀 Iniciando pruebas de generación automática de credenciales\n")
    
    # Crear primer administrador
    admin_creds = test_create_first_admin()
    
    if admin_creds:
        # Crear usuario usando las credenciales del admin
        user_result = test_create_user(admin_creds)
        
        if user_result:
            print("\n✅ Todas las pruebas completadas exitosamente!")
            print("\nResumen de credenciales generadas:")
            print(f"Admin - Nickname: {admin_creds['nickname']}, Password: {admin_creds['password']}")
            print(f"Usuario - Nickname: {user_result['generated_credentials']['nickname']}, Password: {user_result['generated_credentials']['password']}")
        else:
            print("\n❌ Error al crear usuario")
    else:
        print("\n❌ Error al crear administrador")

if __name__ == "__main__":
    main()
