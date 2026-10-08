"""
Analisis de fantoma planar con pylinac (modulo Planar Imaging).

Mide la calidad de imagen del panel kV o MV (EPID) de un acelerador lineal:
  - Bajo contraste  -> que tan bien se distinguen objetos de densidad parecida
  - Alto contraste  -> resolucion espacial (curva rMTF con pares de lineas)
  - Uniformidad, CNR, centro y area del fantoma

Instalacion (una sola vez, en la terminal):
    pip install pylinac

Ejecucion:
    python planar_phantom.py
"""

from pylinac import LeedsTOR
# Otros fantomas del mismo modulo (todos se usan igual):
# from pylinac import LeedsTORBlue, StandardImagingQC3, StandardImagingQCkV,
#     LasVegas, ElektaLasVegas, DoselabMC2kV, DoselabMC2MV, SNCkV, SNCMV,
#     PTWEPIDQC, IBAPrimusA

# ----------------------------------------------------------------------
# CONFIGURACION: cambia solo esta parte
# ----------------------------------------------------------------------
Fantoma = LeedsTOR          # clase del fantoma que vas a analizar
RUTA_IMAGEN = None          # None = imagen demo. Ej: r"C:\examen\leeds.dcm"

UMBRAL_BAJO_CONTRASTE = 0.05   # contraste minimo para que una ROI "pase"
UMBRAL_ALTO_CONTRASTE = 0.5    # rMTF minimo para que una ROI "pase"
SSD = "auto"                   # distancia fuente-fantoma en mm, o "auto"
INVERTIR = False               # True si las ROIs salen giradas/desplazadas
# ----------------------------------------------------------------------


def main():
    # 1) CARGAR la imagen (DICOM del panel) o la imagen de demostracion
    if RUTA_IMAGEN is None:
        fantoma = Fantoma.from_demo_image()
    else:
        fantoma = Fantoma(RUTA_IMAGEN)

    # 2) ANALIZAR: pylinac localiza el fantoma (bordes Canny), calcula su
    #    centro y angulo, coloca las ROIs y mide contraste y rMTF
    fantoma.analyze(
        low_contrast_threshold=UMBRAL_BAJO_CONTRASTE,
        high_contrast_threshold=UMBRAL_ALTO_CONTRASTE,
        ssd=SSD,
        invert=INVERTIR,
    )

    # 3) RESULTADOS en texto
    print(fantoma.results())

    # 4) RESULTADOS numericos individuales
    datos = fantoma.results_data()
    print("\n--- Valores clave ---")
    print("Contraste mediano:        ", datos.median_contrast)
    print("CNR mediano:              ", datos.median_cnr)
    print("ROIs de contraste vistas: ", datos.num_contrast_rois_seen)
    print("Centro del fantoma (x, y):", datos.phantom_center_x_y)
    print("Area del fantoma:         ", datos.phantom_area)
    print("Uniformidad (PIU %):      ", datos.percent_integral_uniformity)

    # Frecuencia espacial (lp/mm) a la que el rMTF cae al 50 %.
    # Solo existe si el fantoma tiene pares de lineas (Las Vegas no tiene).
    if getattr(fantoma, "mtf", None) is not None:
        print("rMTF 50 % (lp/mm):        ", fantoma.mtf.relative_resolution(x=50))

    # 5) GUARDAR imagen analizada y reporte PDF
    fantoma.save_analyzed_image("resultado_fantoma.png")
    fantoma.publish_pdf(
        "reporte_fantoma.pdf",
        notes="Analisis de fantoma planar",
        metadata={"Autor": "Tu nombre", "Equipo": "Linac"},
    )
    print("\nGuardado: resultado_fantoma.png y reporte_fantoma.pdf")

    # 6) MOSTRAR la figura: imagen con ROIs, grafica de bajo contraste y rMTF
    fantoma.plot_analyzed_image(show_roi_labels=True)


if __name__ == "__main__":
    main()
