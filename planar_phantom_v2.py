"""
Analisis de fantomas planares con pylinac (modulo Planar Imaging) - version 2.

Novedades respecto a planar_phantom.py:
  1. Analiza VARIOS fantomas en una sola corrida (ej. Las Vegas + SNC MV-QA).
  2. Avisa cuando un fantoma NO tiene alto contraste (Las Vegas no tiene
     pares de lineas, solo evalua bajo contraste).
  3. Alto contraste completo: rMTF 80/50/30 % y PASA/FALLA por cada ROI.
  4. Expone el umbral de visibilidad (criterio de Rose) que decide si una
     ROI de bajo contraste se "ve".
  5. Compara contra una LINEA BASE con tolerancias y da un veredicto global.

Instalacion (una sola vez, en la terminal):
    pip install pylinac

Ejecucion:
    python planar_phantom_v2.py
"""

import warnings

from pylinac import LasVegas, LeedsTOR, SNCkV, SNCMV
# Otros fantomas del mismo modulo (todos se usan igual):
# from pylinac import LeedsTORBlue, StandardImagingQC3, StandardImagingQCkV,
#     ElektaLasVegas, DoselabMC2kV, DoselabMC2MV, SNCMV12510, PTWEPIDQC,
#     IBAPrimusA

# Oculta dos avisos internos de pylinac que no afectan el resultado
# (pylinac los vuelve a imprimir por su cuenta, por eso no basta filterwarnings)
_mostrar_aviso = warnings.showwarning


def _filtrar_avisos(message, category, *args, **kwargs):
    texto = str(message)
    if "bbox_area" in texto or "MTF resolution wasn't calculated" in texto:
        return
    _mostrar_aviso(message, category, *args, **kwargs)


warnings.showwarning = _filtrar_avisos

# ----------------------------------------------------------------------
# CONFIGURACION: cambia solo esta parte
# ----------------------------------------------------------------------
# Lista de fantomas a analizar. imagen=None usa la imagen demo de pylinac.
# Ejemplo con imagenes reales del hospital:
#   {"fantoma": LasVegas, "imagen": r"C:\examen\lasvegas.dcm"},
#   {"fantoma": SNCMV,    "imagen": r"C:\examen\snc_mv.dcm"},
ANALISIS = [
    {"fantoma": LeedsTOR, "imagen": None},   # kV: bajo + alto contraste
    {"fantoma": SNCkV, "imagen": None},      # kV: bajo + alto contraste
    {"fantoma": SNCMV, "imagen": None},      # MV (EPID): bajo + alto contraste
    {"fantoma": LasVegas, "imagen": None},   # MV (EPID): SOLO bajo contraste
]

UMBRAL_BAJO_CONTRASTE = 0.05   # contraste minimo de una ROI de bajo contraste
UMBRAL_ALTO_CONTRASTE = 0.5    # rMTF minimo para que una ROI de alto contraste pase
UMBRAL_VISIBILIDAD = 100       # visibilidad (Rose) minima para que una ROI "se vea"
SSD = "auto"                   # distancia fuente-fantoma en mm, o "auto"
INVERTIR = False               # True si las ROIs salen giradas/desplazadas

# LINEA BASE: valores de referencia de cada fantoma (se miden el dia de la
# puesta en marcha). Aqui se usan los resultados de las imagenes demo.
# Si un fantoma no aparece aqui, se analiza pero no se compara.
LINEA_BASE = {
    "LeedsTOR": {"mtf50": 1.63, "lc_vistas": 10, "piu": 91.8},
    "SNCkV": {"mtf50": 1.70, "lc_vistas": 4, "piu": 98.7},
    "SNCMV": {"mtf50": 0.47, "lc_vistas": 3, "piu": 98.4},
    "LasVegas": {"lc_vistas": 12, "piu": 98.4},
}
# Tolerancias: cuanto puede alejarse cada valor de su linea base.
TOL_MTF50_RELATIVA = 0.10      # +-10 % del MTF50 de referencia
TOL_LC_VISTAS = 1              # se permite ver 1 ROI menos que la referencia
TOL_PIU = 2.0                  # +-2 puntos de uniformidad (%)

GUARDAR_PDF = True
MOSTRAR_FIGURAS = True         # False para solo guardar las imagenes
AUTOR = "Tu nombre"
EQUIPO = "Linac"
# ----------------------------------------------------------------------


def analizar(fantoma_clase, imagen):
    """Carga y analiza un fantoma. Devuelve el objeto de pylinac analizado."""
    if imagen is None:
        fantoma = fantoma_clase.from_demo_image()
    else:
        fantoma = fantoma_clase(imagen)
    fantoma.analyze(
        low_contrast_threshold=UMBRAL_BAJO_CONTRASTE,
        high_contrast_threshold=UMBRAL_ALTO_CONTRASTE,
        visibility_threshold=UMBRAL_VISIBILIDAD,
        ssd=SSD,
        invert=INVERTIR,
    )
    return fantoma


def reporte_bajo_contraste(fantoma):
    """Tabla de cada ROI de bajo contraste: contraste, CNR, visibilidad."""
    print("\n  BAJO CONTRASTE (umbral de visibilidad = %g)" % UMBRAL_VISIBILIDAD)
    print("  ROI  Contraste    CNR   Visibilidad  Se ve?")
    for i, roi in enumerate(fantoma.low_contrast_rois):
        print(
            "  %3d  %9.4f  %6.2f  %11.1f  %s"
            % (i, roi.contrast, roi.contrast_to_noise, roi.visibility,
               "SI" if roi.passed_visibility else "no")
        )
    vistas = fantoma.results_data().num_contrast_rois_seen
    print("  ROIs vistas: %d de %d" % (vistas, len(fantoma.low_contrast_rois)))
    return vistas


def mtf_seguro(mtf, porcentaje):
    """rMTF al porcentaje pedido; None si pylinac tendria que extrapolar."""
    if porcentaje / 100 < min(mtf.norm_mtfs.values()):
        return None
    return mtf.relative_resolution(x=porcentaje)


def reporte_alto_contraste(fantoma):
    """rMTF 80/50/30 % y PASA/FALLA de cada ROI de alto contraste."""
    mtf = getattr(fantoma, "mtf", None)
    if mtf is None:
        print("\n  ALTO CONTRASTE: NO EVALUADO")
        print("  Este fantoma no tiene pares de lineas, asi que pylinac no")
        print("  calcula rMTF. Para alto contraste usa otro fantoma (ej. SNC MV-QA).")
        return None

    print("\n  ALTO CONTRASTE (umbral rMTF = %g)" % UMBRAL_ALTO_CONTRASTE)
    print("  ROI   lp/mm   rMTF   Resultado")
    for i, (lpmm, valor) in enumerate(mtf.norm_mtfs.items()):
        resultado = "PASA" if valor >= UMBRAL_ALTO_CONTRASTE else "falla"
        print("  %3d  %6.2f  %5.3f   %s" % (i, lpmm, valor, resultado))

    resultados = {}
    for p in (80, 50, 30):
        resultados[p] = mtf_seguro(mtf, p)
        texto = "%.2f lp/mm" % resultados[p] if resultados[p] is not None \
            else "fuera del rango medido"
        print("  rMTF %d %%: %s" % (p, texto))
    return resultados[50]


def comparar_con_linea_base(nombre, medido):
    """Compara lo medido contra LINEA_BASE. Devuelve True/False/None."""
    base = LINEA_BASE.get(nombre)
    if base is None:
        print("\n  LINEA BASE: no definida para %s, no se compara." % nombre)
        return None

    print("\n  COMPARACION CON LINEA BASE")
    pruebas = []
    if "mtf50" in base:
        ref, val = base["mtf50"], medido["mtf50"]
        ok = val is not None and abs(val - ref) <= TOL_MTF50_RELATIVA * ref
        pruebas.append(("MTF50 (lp/mm)", ref, val, "+-%d %%" % (TOL_MTF50_RELATIVA * 100), ok))
    if "lc_vistas" in base:
        ref, val = base["lc_vistas"], medido["lc_vistas"]
        ok = val >= ref - TOL_LC_VISTAS
        pruebas.append(("ROIs bajo contraste vistas", ref, val, "-%d" % TOL_LC_VISTAS, ok))
    if "piu" in base:
        ref, val = base["piu"], medido["piu"]
        ok = abs(val - ref) <= TOL_PIU
        pruebas.append(("Uniformidad PIU (%)", ref, val, "+-%g" % TOL_PIU, ok))

    for prueba, ref, val, tol, ok in pruebas:
        val_txt = "-" if val is None else "%.2f" % val
        print("  %-27s ref %6.2f  medido %6s  tol %-6s  %s"
              % (prueba, ref, val_txt, tol, "PASA" if ok else "FALLA"))
    return all(ok for *_, ok in pruebas)


def main():
    resumen = []
    for item in ANALISIS:
        clase = item["fantoma"]
        nombre = clase.__name__
        print("\n" + "=" * 70)
        print(" %s (%s)" % (clase.common_name, item["imagen"] or "imagen demo"))
        print("=" * 70)

        try:
            fantoma = analizar(clase, item["imagen"])
        except Exception as error:
            # Lo mas comun: no encontro el fantoma o la imagen esta invertida
            print("  ERROR al analizar: %s" % error)
            print("  Revisa la ruta de la imagen; si es correcta, prueba INVERTIR = True\n  o confirma que la imagen es de este fantoma.")
            resumen.append([clase.common_name, "-", "-", "-", "ERROR"])
            continue

        datos = fantoma.results_data()
        print("  Contraste mediano: %.4f   CNR mediano: %.2f"
              % (datos.median_contrast, datos.median_cnr))
        print("  Centro (x, y): %s   Area: %.0f px"
              % (datos.phantom_center_x_y, datos.phantom_area))

        vistas = reporte_bajo_contraste(fantoma)
        mtf50 = reporte_alto_contraste(fantoma)
        medido = {
            "mtf50": mtf50,
            "lc_vistas": vistas,
            "piu": datos.percent_integral_uniformity,
        }
        veredicto = comparar_con_linea_base(nombre, medido)

        fantoma.save_analyzed_image("resultado_%s.png" % nombre)
        if GUARDAR_PDF:
            fantoma.publish_pdf(
                "reporte_%s.pdf" % nombre,
                notes="Analisis de fantoma planar",
                metadata={"Autor": AUTOR, "Equipo": EQUIPO},
            )
        if MOSTRAR_FIGURAS:
            fantoma.plot_analyzed_image(show_roi_labels=True)

        resumen.append([
            clase.common_name,
            "%d/%d" % (vistas, len(fantoma.low_contrast_rois)),
            "%.2f" % mtf50 if mtf50 is not None else "no evaluado",
            "%.1f" % medido["piu"],
            {True: "PASA", False: "FALLA", None: "sin linea base"}[veredicto],
        ])

    # Tabla final con todos los fantomas
    print("\n" + "=" * 70)
    print(" RESUMEN")
    print("=" * 70)
    encabezado = ["Fantoma", "LC vistas", "MTF50 lp/mm", "PIU %", "Veredicto"]
    print("  %-20s %-10s %-12s %-7s %s" % tuple(encabezado))
    for fila in resumen:
        print("  %-20s %-10s %-12s %-7s %s" % tuple(fila))
    print("\nImagenes guardadas como resultado_<fantoma>.png")


if __name__ == "__main__":
    main()
