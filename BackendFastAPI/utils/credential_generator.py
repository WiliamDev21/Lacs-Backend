import random
import string
import secrets

def generate_nickname(nombre: str, apellido_paterno: str, apellido_materno: str) -> str:
    """
    Genera un nickname basado en las dos primeras letras del nombre y apellidos
    más 4 letras aleatorias, todo en mayúsculas.
    
    Args:
        nombre: Nombre de la persona
        apellido_paterno: Apellido paterno
        apellido_materno: Apellido materno
        
    Returns:
        Nickname generado (ej: JUAN PEREZ LOPEZ -> JUPELO + 4 letras aleatorias)
    """
    # Limpiar y obtener las primeras dos letras de cada campo
    nombre_clean = nombre.strip().upper()[:2]
    apellido_p_clean = apellido_paterno.strip().upper()[:2]
    apellido_m_clean = apellido_materno.strip().upper()[:2]
    
    # Generar 4 letras aleatorias
    random_letters = ''.join(secrets.choice(string.ascii_uppercase) for _ in range(4))
    
    # Construir nickname
    nickname = f"{nombre_clean}{apellido_p_clean}{apellido_m_clean}{random_letters}"
    
    return nickname

def generate_secure_password(length: int = 12) -> str:
    """
    Genera una contraseña segura aleatoria.
    
    Args:
        length: Longitud de la contraseña (default: 12)
        
    Returns:
        Contraseña segura generada
    """
    # Definir caracteres permitidos
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special_chars = "!@#$%&*"
    
    # Asegurar que la contraseña tenga al menos un caracter de cada tipo
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special_chars)
    ]
    
    # Completar la longitud restante con caracteres aleatorios
    all_chars = lowercase + uppercase + digits + special_chars
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))
    
    # Mezclar la contraseña para que no tenga un patrón predecible
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)

def generate_admin_credentials(nombre: str, apellido_paterno: str, apellido_materno: str) -> dict:
    """
    Genera credenciales completas para un administrador.
    
    Args:
        nombre: Nombre del administrador
        apellido_paterno: Apellido paterno
        apellido_materno: Apellido materno
        
    Returns:
        Diccionario con nickname y password generados
    """
    return {
        "nickname": generate_nickname(nombre, apellido_paterno, apellido_materno),
        "password": generate_secure_password()
    }

def generate_user_credentials(nombre: str, apellido_paterno: str, apellido_materno: str) -> dict:
    """
    Genera credenciales completas para un usuario.
    
    Args:
        nombre: Nombre del usuario
        apellido_paterno: Apellido paterno
        apellido_materno: Apellido materno
        
    Returns:
        Diccionario con nickname y password generados
    """
    return {
        "nickname": generate_nickname(nombre, apellido_paterno, apellido_materno),
        "password": generate_secure_password()
    }
