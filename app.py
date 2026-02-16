import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ══════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════

st.set_page_config(
    page_title="Disponibilidad de Materiales",
    page_icon="📦",
    layout="wide",
)

st.markdown("""
<style>
    .main .block-container { padding-top: 2rem; max-width: 1200px; }
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border: 1px solid #475569;
        border-radius: 12px;
        padding: 1rem 1.2rem;
    }
    div[data-testid="metric-container"] label { color: #94a3b8 !important; }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #f1f5f9 !important; }
    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%);
        border-radius: 16px;
        padding: 2rem 2.5rem;
        margin-bottom: 2rem;
    }
    .main-header h1 { color: #f1f5f9; font-size: 1.8rem; margin: 0; }
    .main-header p { color: #94a3b8; margin: 0.3rem 0 0 0; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# CARGAR DATOS
# ══════════════════════════════════════════════════

@st.cache_data
def cargar_datos():
    df = pd.read_csv("datos_disponibilidad.csv")
    df["Nivel_Stock"] = pd.cut(
        df["Disponible"],
        bins=[-1, 0, 10, 50, float("inf")],
        labels=["Agotado", "Bajo", "Medio", "Alto"],
    )
    return df

df = cargar_datos()

# ══════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
    <h1>📦 Portal de Disponibilidad de Materiales</h1>
    <p>Consulta de existencias, precios y categorías de SKUs</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# MÉTRICAS
# ══════════════════════════════════════════════════

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("SKUs Totales", f"{len(df):,}")
col2.metric("Disponibilidad Total", f"{df['Disponible'].sum():,.0f}")
col3.metric("Categorías", df["Categoria"].nunique())
col4.metric("Agotados", f"{(df['Disponible'] == 0).sum():,}")
col5.metric("Stock Bajo (≤10)", f"{((df['Disponible'] > 0) & (df['Disponible'] <= 10)).sum():,}")

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════

tab_buscar, tab_resumen, tab_alertas, tab_descargar = st.tabs(
    ["🔍 Buscar SKUs", "📊 Resumen", "⚠️ Alertas de Stock", "📥 Descargar"]
)

# ━━━━━━━ BUSCAR ━━━━━━━
with tab_buscar:
    col_search, col_cat = st.columns([2, 1])

    with col_search:
        busqueda = st.text_input(
            "Buscar por número de parte o descripción",
            placeholder="Ej: RODAMIENTO, 01100342, BALERO...",
        )

    with col_cat:
        categorias = ["Todas"] + sorted(df["Categoria"].unique().tolist())
        cat_filtro = st.selectbox("Categoría", categorias)

    col_stock, col_sort = st.columns(2)
    with col_stock:
        nivel_filtro = st.multiselect(
            "Nivel de stock",
            ["Alto", "Medio", "Bajo", "Agotado"],
            default=None,
            placeholder="Todos los niveles",
        )
    with col_sort:
        orden = st.selectbox(
            "Ordenar por",
            ["Numero_de_Parte", "Disponible (↑)", "Disponible (↓)", "Precio (↑)", "Precio (↓)"],
        )

    # Aplicar filtros
    df_filtrado = df.copy()

    if busqueda:
        mask = (
            df_filtrado["Numero_de_Parte"].str.contains(busqueda.upper(), case=False, na=False)
            | df_filtrado["Descripcion"].str.contains(busqueda.upper(), case=False, na=False)
        )
        df_filtrado = df_filtrado[mask]

    if cat_filtro != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Categoria"] == cat_filtro]

    if nivel_filtro:
        df_filtrado = df_filtrado[df_filtrado["Nivel_Stock"].isin(nivel_filtro)]

    if orden == "Disponible (↑)":
        df_filtrado = df_filtrado.sort_values("Disponible")
    elif orden == "Disponible (↓)":
        df_filtrado = df_filtrado.sort_values("Disponible", ascending=False)
    elif orden == "Precio (↑)":
        df_filtrado = df_filtrado.sort_values("Precio")
    elif orden == "Precio (↓)":
        df_filtrado = df_filtrado.sort_values("Precio", ascending=False)

    st.caption(f"Mostrando **{len(df_filtrado):,}** de {len(df):,} SKUs")

    st.dataframe(
        df_filtrado[["Numero_de_Parte", "Descripcion", "Categoria", "Disponible", "Comprometido", "Precio", "Nivel_Stock"]],
        use_container_width=True,
        height=500,
        column_config={
            "Numero_de_Parte": st.column_config.TextColumn("# Parte", width="small"),
            "Descripcion": st.column_config.TextColumn("Descripción", width="large"),
            "Categoria": st.column_config.TextColumn("Categoría", width="small"),
            "Disponible": st.column_config.NumberColumn("Disponible", format="%d"),
            "Comprometido": st.column_config.NumberColumn("Comprometido", format="%d"),
            "Precio": st.column_config.NumberColumn("Precio (MXN)", format="$%.2f"),
            "Nivel_Stock": st.column_config.TextColumn("Nivel", width="small"),
        },
    )

# ━━━━━━━ RESUMEN ━━━━━━━
with tab_resumen:
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        cat_summary = df.groupby("Categoria").agg(
            SKUs=("Numero_de_Parte", "count"),
            Disponible=("Disponible", "sum"),
        ).reset_index().sort_values("SKUs", ascending=True)

        fig1 = px.bar(
            cat_summary, y="Categoria", x="SKUs",
            orientation="h", title="SKUs por Categoría",
            color="SKUs", color_continuous_scale="Blues",
        )
        fig1.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0", showlegend=False, height=400,
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col_chart2:
        stock_counts = df["Nivel_Stock"].value_counts().reset_index()
        stock_counts.columns = ["Nivel", "Cantidad"]
        colors_map = {"Alto": "#10b981", "Medio": "#f59e0b", "Bajo": "#ef4444", "Agotado": "#6b7280"}

        fig2 = px.pie(
            stock_counts, values="Cantidad", names="Nivel",
            title="Distribución de Niveles de Stock",
            color="Nivel", color_discrete_map=colors_map, hole=0.4,
        )
        fig2.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0", height=400,
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("#### Top 20 SKUs con Mayor Disponibilidad")
    top20 = df.nlargest(20, "Disponible")[["Numero_de_Parte", "Descripcion", "Categoria", "Disponible", "Precio"]]
    fig3 = px.bar(
        top20.sort_values("Disponible"), y="Numero_de_Parte", x="Disponible",
        orientation="h", color="Disponible", color_continuous_scale="Greens",
        hover_data=["Descripcion", "Precio"],
    )
    fig3.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="#e2e8f0", height=600, showlegend=False,
    )
    st.plotly_chart(fig3, use_container_width=True)

# ━━━━━━━ ALERTAS ━━━━━━━
with tab_alertas:
    st.markdown("#### ⚠️ SKUs Agotados o con Stock Bajo")
    umbral = st.slider("Umbral de stock bajo", min_value=0, max_value=100, value=10, step=5)
    df_alerta = df[df["Disponible"] <= umbral].sort_values("Disponible")

    col_a, col_b = st.columns(2)
    col_a.metric("Agotados (0 unidades)", f"{(df_alerta['Disponible'] == 0).sum():,}")
    col_b.metric(f"Stock ≤ {umbral} unidades", f"{len(df_alerta):,}")

    st.dataframe(
        df_alerta[["Numero_de_Parte", "Descripcion", "Categoria", "Disponible", "Comprometido", "Precio"]],
        use_container_width=True,
        height=500,
        column_config={
            "Numero_de_Parte": st.column_config.TextColumn("# Parte", width="small"),
            "Disponible": st.column_config.NumberColumn("Disp.", format="%d"),
            "Comprometido": st.column_config.NumberColumn("Comp.", format="%d"),
            "Precio": st.column_config.NumberColumn("Precio", format="$%.2f"),
        },
    )

# ━━━━━━━ DESCARGAR ━━━━━━━
with tab_descargar:
    st.markdown("#### 📥 Exportar Reporte")
    st.caption(f"{len(df):,} SKUs en total")

    from io import BytesIO
    output = BytesIO()
    df.drop(columns=["Nivel_Stock"]).to_excel(output, index=False, sheet_name="Disponibilidad", engine="openpyxl")

    st.download_button(
        "⬇️ Descargar Excel Completo",
        data=output.getvalue(),
        file_name=f"disponibilidad_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

# ━━━━━━━ FOOTER ━━━━━━━
st.divider()
st.caption("Portal de Disponibilidad de Materiales · Powered by Streamlit")
