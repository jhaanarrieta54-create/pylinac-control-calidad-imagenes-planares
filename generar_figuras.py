"""
Genera las figuras del documento de fundamento teorico (README.md).

Usa la imagen demo del fantoma Leeds TOR incluida en pylinac y guarda
las figuras en la misma carpeta que el README. Requiere: pip install pylinac
"""
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pylinac import LeedsTOR

warnings.filterwarnings("ignore")  # avisos de versiones de librerias, no afectan

SALIDA = Path(__file__).resolve().parent
DPI = 150

fantoma = LeedsTOR.from_demo_image()

# 1) Imagen cruda, antes del analisis
fig, ax = plt.subplots(figsize=(8, 6))
ax.imshow(fantoma.image.array, cmap="gray")
ax.set_title("Imagen kV del fantoma Leeds TOR (sin analizar)")
ax.axis("off")
fig.savefig(SALIDA / "01_imagen_cruda.png", dpi=DPI, bbox_inches="tight")
plt.close(fig)

# 2) Analisis con los mismos parametros del script del examen
fantoma.analyze(low_contrast_threshold=0.05, high_contrast_threshold=0.5,
                ssd="auto", invert=False)

# 3) Figuras de pylinac por separado: imagen, bajo contraste y rMTF
figs, nombres = fantoma.plot_analyzed_image(show=False, split_plots=True,
                                            show_roi_labels=True, figsize=(9, 7))
destino = {"image": "02_imagen_analizada.png",
           "low_contrast": "03_bajo_contraste.png",
           "high_contrast": "04_rmtf.png"}
for f, n in zip(figs, nombres):
    f.savefig(SALIDA / destino.get(n, f"{n}.png"), dpi=DPI, bbox_inches="tight")
    plt.close(f)

# 4) Figura resumen (las tres juntas, como la ventana del script)
fantoma.plot_analyzed_image(show=False, show_roi_labels=True, figsize=(18, 6))
fig = plt.gcf()
fig.savefig(SALIDA / "05_resumen.png", dpi=DPI, bbox_inches="tight")
plt.close(fig)

# 5) Visibilidad de Rose por ROI frente al umbral (criterio de "vista")
rois = fantoma.low_contrast_rois
vis = [r.visibility for r in rois]
umbral = rois[0].visibility_threshold
colores = ["tab:green" if r.passed_visibility else "tab:red" for r in rois]
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.bar(range(len(vis)), vis, color=colores)
ax.axhline(umbral, color="k", ls="--", label=f"Umbral de visibilidad = {umbral}")
ax.set_yscale("log")
ax.set_xticks(range(len(vis)))
ax.set_xlabel("ROI de bajo contraste (LC#)")
ax.set_ylabel("Visibilidad (escala log)")
ax.set_title("Visibilidad de Rose por ROI: verde = vista, rojo = no vista")
ax.legend()
fig.savefig(SALIDA / "06_visibilidad_rose.png", dpi=DPI, bbox_inches="tight")
plt.close(fig)

# 6) Tabla de resultados por consola
d = fantoma.results_data()
print(fantoma.results())
print(f"PIU (%): {d.percent_integral_uniformity:.2f}")
print("ROI  Contraste  CNR     Visibilidad  Vista")
for i, r in enumerate(rois):
    print(f"LC{i:<3}{r.contrast:9.4f}{r.contrast_to_noise:8.2f}"
          f"{r.visibility:12.1f}   {'si' if r.passed_visibility else 'no'}")
print("lp/mm  rMTF")
for lp, v in fantoma.mtf.norm_mtfs.items():
    print(f"{lp:5.2f}  {v:.3f}")
print("Figuras guardadas en", SALIDA)
