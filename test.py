from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import pandas as pd
from itertools import product
from tqdm import tqdm

# Configuración inicial
SPREADSHEET_ID = "1LnQY2tABOaIN86_q80p24RNGFR3h_eTI9JVOF6HfeB4"
RANGE_NAME = "Verificador!AF:AJ"
CREDENTIALS_FILE = "key.json"

# Cargar credenciales y cliente de Google Sheets
credentials = Credentials.from_service_account_file(
    CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
)
service = build("sheets", "v4", credentials=credentials)

# Leer datos de la hoja de cálculo
sheet = service.spreadsheets()
result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
data = result.get("values", [])

# Convertir a DataFrame
df = pd.DataFrame(data[1:], columns=data[0])
df.columns = df.columns.str.strip()

# Reemplazar valores "-" por NaN y convertir columnas numéricas
df.replace("-", pd.NA, inplace=True)
precio_cols = [col for col in df.columns[2:] if col != "Lider"]  # Excluir 'Lider'

for col in precio_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Reemplazar NaN por 0
df.fillna(0, inplace=True)

# Verificar que no haya valores no numéricos
for col in precio_cols:
    if not pd.api.types.is_numeric_dtype(df[col]):
        print(f"Error: La columna {col} contiene valores no numéricos.")
        df[col] = pd.to_numeric(df[col], errors="coerce")  # Reconversión forzada
        df.fillna(0, inplace=True)

# Ajustar precios: multiplicar por 100 si el valor es menor a 300
df[precio_cols] = df[precio_cols].applymap(lambda x: x * 100 if 0 < x < 300 else x)

# Eliminar filas donde todas las columnas de precios sean 0
df = df.loc[~(df[precio_cols].sum(axis=1) == 0)]

print("Datos limpios ajustados:")
print(df)

# Evaluación de combinaciones
supermercados = precio_cols  # ['Jumbo', 'Unimarc', 'Santa Isabel']
combinaciones = list(product([0, 1], repeat=len(supermercados)))
print(f"Número de combinaciones a evaluar: {len(combinaciones)}")

for combinacion in tqdm(combinaciones, desc="Evaluando combinaciones"):
    costo_por_super = {super: 0 for super in supermercados}
    for i, incluir in enumerate(combinacion):
        if incluir == 1:
            for super in supermercados:
                try:
                    costo_por_super[super] += float(df.iloc[i][super])
                except ValueError as e:
                    print(f"Error procesando fila {i}, columna {super}: {e}")
                    costo_por_super[super] += 0  # Valor predeterminado en caso de error

    print(costo_por_super)


# Configuración de costos de envío
envio = {"Lider": 500, "Jumbo": 400, "Unimarc": 300, "Santa Isabel":9000, "Lider2":2340}  # Ejemplo de costos de envío
minimo_envio_gratis = {"Lider": 2, "Jumbo": 3, "Unimarc": 4 , "Santa Isabel": 5,"Lider2":23}

# Productos a comprar
productos_a_comprar = df["Nombre Producto"]

# Crear combinaciones posibles
supermercados = df.columns[1:]  # Excluye la columna de productos
combinaciones = list(product(supermercados, repeat=len(productos_a_comprar)))

print(f"Número de combinaciones a evaluar: {len(combinaciones)}")

# Evaluar cada combinación con seguimiento
mejor_costo = float("inf")
mejor_opcion = None

for combo in tqdm(combinaciones, desc="Evaluando combinaciones", unit="combinación"):
    # Inicializar costos por supermercado
    costo_por_super = {super: 0 for super in supermercados}
    
    # Calcular costos por producto
    for i, super in enumerate(combo):
        costo_por_super[super] += df.iloc[i][super]
    
    # Agregar costos de envío
    costo_total = 0
    for super, costo in costo_por_super.items():
        if costo > 0 and costo < minimo_envio_gratis[super]:
            costo += envio[super]
        costo_total += costo
    
    # Comparar con el mejor costo
    if costo_total < mejor_costo:
        mejor_costo = costo_total
        mejor_opcion = combo

# Mostrar resultado
print("\nMejor combinación:")
print(mejor_opcion)
print(f"Costo total: {mejor_costo}")
