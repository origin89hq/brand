"""Package native raster exports as multi-resolution ICO files."""
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
Image.open(ROOT/'icons/favicon-48.png').save(ROOT/'icons/favicon.ico',sizes=[(16,16),(32,32),(48,48)])
Image.open(ROOT/'icons/offgrid-flat-1024.png').save(ROOT/'icons/offgrid.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
