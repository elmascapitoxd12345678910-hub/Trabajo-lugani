# E-Commerce REST API

API REST profesional para plataformas de comercio electrónico desarrollada con Python y FastAPI, diseñada con arquitectura modular, escalable y en cumplimiento con los estándares normativos y legales de la República Argentina.

---

## Características Principales

* **Framework de alto rendimiento**: Construida sobre [FastAPI](https://fastapi.tiangolo.com/) y el servidor ASGI [Uvicorn](https://www.uvicorn.org/).
* **Arquitectura modular**: Separación estricta de responsabilidades (`routers`, `models`, `schemas`, `services`, `core`).
* **Documentación interactiva automática**: Generación nativa de especificaciones OpenAPI (Swagger y ReDoc).
* **Cumplimiento legal por diseño**: Estructura preparada para satisfacer los requerimientos regulatorios de comercio electrónico en Argentina.

---

## Guía de Instalación y Ejecución Rápida

### Requisitos Previos

* Python 3.10 o superior instalado.
* Gestor de paquetes `pip`.

### 1. Clonar o acceder al directorio del proyecto

```bash
cd mi-ecommerce
```

### 2. Creación del entorno virtual

Crea un entorno virtual aislado para gestionar las dependencias del proyecto:

```bash
python -m venv .venv
```

### 3. Activación del entorno virtual

* **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
  *(En caso de restricciones de ejecución en PowerShell, habilitar previamente con `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

* **Windows (Command Prompt / CMD):**
  ```cmd
  .\.venv\Scripts\activate.bat
  ```

* **Linux / macOS:**
  ```bash
  source .venv/bin/activate
  ```

### 4. Instalación de dependencias

Instala los paquetes mínimos necesarios listados en `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 5. Iniciar el servidor de desarrollo

Ejecuta el servidor ASGI Uvicorn con recarga automática activa (*hot reload*):

```bash
uvicorn app.main:app --reload
```

El servicio estará disponible en: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## Documentación Interactiva de la API

FastAPI genera automáticamente documentación interactiva basada en OpenAPI:

* **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  
  Permite explorar y probar interactivamente todos los endpoints disponibles.
* **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)  
  Documentación estructurada y detallada de los esquemas y contratos de datos.

---

## Marco Legal y Cumplimiento Normativo (Argentina)

Esta plataforma y sus interfaces de programación de aplicaciones (APIs) han sido concebidas para operar en estricto cumplimiento del marco legal aplicable al comercio electrónico en la República Argentina:

### 1. Ley 24.240 – Defensa del Consumidor
* **Deber de información (Art. 4°)**: Toda la información provista a través de los endpoints de productos, ofertas y facturación debe ser veraz, clara, precisa y detallada respecto de las características esenciales de los bienes y servicios, disponibilidad de stock, precio total final (incluyendo tributos) y modalidades de pago y entrega.
* **Términos y condiciones contractuales (Art. 37 y concordantes)**: Prohibición de cláusulas abusivas o lesivas para los derechos de los consumidores en las transacciones digitales.

### 2. Resolución 424/2020 – Secretaría de Comercio Interior (Botón de Arrepentimiento)
* **Revocación de la compra digital**: Exigencia legal de proveer de forma visible, accesible y destacada el mecanismo para que el consumidor pueda solicitar la revocación de la aceptación de compra dentro del plazo legal de 10 (diez) días corridos desde la celebración del contrato o recepción del producto, sin costo ni penalización alguna.
* **Gestión técnica de solicitudes**: La API deberá prever la recepción, registro y emisión de un código identificador único del trámite de arrepentimiento dentro de las 24 horas hábiles posteriores a la solicitud del usuario.

### 3. Ley 25.326 – Protección de los Datos Personales (Habeas Data)
* **Principio de licitud y finalidad (Art. 4°)**: Los datos personales recopilados (identificación de clientes, domicilios, información transaccional) solo serán tratados con fines legítimos propios de la operatoria del e-commerce.
* **Seguridad de los datos (Art. 9°)**: Implementación obligatoria de medidas técnicas y organizativas para garantizar la confidencialidad, integridad y protección contra el acceso no autorizado.
* **Derechos ARCO (Acceso, Rectificación, Cancelación y Oposición)**: Los usuarios conservan el derecho irrestricto de acceder a sus datos personales almacenados en la plataforma, así como de solicitar su rectificación, actualización o supresión.

---

## Estructura del Proyecto

```text
mi-ecommerce/
├── .gitignore          # Reglas de exclusión para Git
├── README.md           # Documentación general y legal del proyecto
├── requirements.txt    # Dependencias del proyecto
└── app/
    ├── main.py         # Punto de entrada de la aplicación FastAPI
    ├── core/           # Configuraciones globales, middlewares y seguridad
    ├── models/         # Modelos de persistencia (ORM / Base de datos)
    ├── routers/        # Endpoints y rutas HTTP segmentadas
    ├── schemas/        # Modelos de validación y DTOs (Pydantic)
    └── services/       # Lógica de negocio y servicios de aplicación
```
