import pandas as pd
from io import StringIO
from datetime import datetime

print("=" * 50)
print("  PROCESANDO DATOS DE SAP")
print("=" * 50)

#  1. LEER INVENTARIO 
print("\n📦 Leyendo inventario...")
with open("data/Inventory in Warehouse Report (Detailed) 16.txt", "rb") as f:
    raw = f.read().decode("utf-16-le").replace("\ufeff", "")

inv = pd.read_csv(StringIO(raw), sep="\t", dtype=str, on_bad_lines="skip")
inv.columns = inv.columns.str.strip()
inv = inv[inv["Item No."].notna() & (inv["Item No."].str.strip() != "")].copy()
inv["Item No."] = inv["Item No."].str.strip()

for col in ["In Stock", "Committed", "Ordered", "Available", "Item Price", "Total"]:
    if col in inv.columns:
        inv[col] = inv[col].str.replace('"', "", regex=False).str.replace(",", "", regex=False).str.strip()
        inv[col] = pd.to_numeric(inv[col], errors="coerce").fillna(0)

inv = inv[["Item No.", "Item Description", "In Stock", "Committed", "Ordered", "Available"]].copy()
print(f"   ✅ {len(inv):,} SKUs encontrados")

# 2. LEER PRECIOS 
print("\n💰 Leyendo precios...")
with open("data/Price Report 16.txt", "rb") as f:
    raw = f.read().decode("utf-16-le").replace("\ufeff", "")

precios = pd.read_csv(StringIO(raw), sep="\t", dtype=str, on_bad_lines="skip")
precios.columns = precios.columns.str.strip()
precios = precios[precios["Item No."].notna() & (precios["Item No."].str.strip() != "")].copy()
precios["Item No."] = precios["Item No."].str.strip()
precios["Primary Currency - Price"] = (
    precios["Primary Currency - Price"]
    .str.replace('"', "", regex=False)
    .str.replace(",", "", regex=False)
    .str.strip()
)
precios["Primary Currency - Price"] = pd.to_numeric(precios["Primary Currency - Price"], errors="coerce").fillna(0)
precios = precios.drop_duplicates(subset="Item No.", keep="last")
precios = precios[["Item No.", "Primary Currency - Price"]].rename(
    columns={"Primary Currency - Price": "Precio"}
)
print(f"   ✅ {len(precios):,} precios cargados")

# 3. LEER DICCIONARIO
print("\n📋 Leyendo diccionario de categorías...")
dicc = pd.read_excel("data/diccionario.xlsx", dtype=str)
dicc.columns = dicc.columns.str.strip()

# Detectar columnas automáticamente
col_id = [c for c in dicc.columns if "part" in c.lower() and "id" in c.lower()]
col_cat = [c for c in dicc.columns if "categ" in c.lower()]

if col_id and col_cat:
    dicc = dicc[[col_id[0], col_cat[0]]].copy()
else:
    dicc = dicc.iloc[:, [0, -1]].copy()

dicc.columns = ["Item No.", "Categoria"]
dicc["Item No."] = dicc["Item No."].str.strip()
dicc["Categoria"] = dicc["Categoria"].str.strip().str.upper()
dicc = dicc.drop_duplicates(subset="Item No.", keep="first")
print(f"   ✅ {len(dicc):,} categorías cargadas")

# 4. CRUZAR TODO
print("\n🔗 Cruzando datos...")
df = inv.merge(precios, on="Item No.", how="left")
df = df.merge(dicc, on="Item No.", how="left")
df["Precio"] = df["Precio"].fillna(0)
df["Categoria"] = df["Categoria"].fillna("SIN CATEGORÍA")

# Renombrar columnas a español
df = df.rename(columns={
    "Item No.": "Numero_de_Parte",
    "Item Description": "Descripcion",
    "In Stock": "En_Stock",
    "Committed": "Comprometido",
    "Ordered": "Pedido",
    "Available": "Disponible",
})

# Reordenar
df = df[["Numero_de_Parte", "Descripcion", "Categoria", "En_Stock", "Comprometido", "Pedido", "Disponible", "Precio"]]
df = df.sort_values(["Categoria", "Numero_de_Parte"]).reset_index(drop=True)

# 5. GUARDAR CSV LIMPIO
df.to_csv("datos_disponibilidad.csv", index=False, encoding="utf-8")

print("\n" + "=" * 50)
print(f"  ✅ LISTO - {len(df):,} SKUs procesados")
print(f"  📄 Archivo guardaya do: datos_disponibilidad.csv")
print(f"  📅 Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 50)

# Resumen rápido
print(f"\n  Categorías: {df['Categoria'].nunique()}")
print(f"  Disponibilidad total: {df['Disponible'].sum():,.0f} unidades")
print(f"  Agotados: {(df['Disponible'] == 0).sum():,} SKUs")
print(f"  Stock bajo (≤10): {((df['Disponible'] > 0) & (df['Disponible'] <= 10)).sum():,} SKUs")