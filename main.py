import os
import ezdxf
from osgeo import gdal
from PIL import Image

def process_directories(orto_dir, dxf_dir):
    dxf_orto_dict = {}

    for file_name in os.listdir(orto_dir):
        if file_name.endswith('.tif'):
            orto_name = file_name.split('.')[0]
            if orto_name.endswith('_'):
                orto_name = orto_name[:-1]

            path_dxf_subdir = os.path.join(dxf_dir, orto_name)
            dxf_path = get_dxf_path(path_dxf_subdir)

            if dxf_path:
                dxf_orto_dict[dxf_path] = os.path.join(orto_dir, file_name)
    
    for dxf_path, orto_path in dxf_orto_dict.items():
        export_regions_from_layer(orto_path, dxf_path)


def get_dxf_path(path_dxf_dir):
    if os.path.exists(path_dxf_dir):
        for file_name in os.listdir(path_dxf_dir):
            if 'Quadra' in file_name:
                return os.path.join(path_dxf_dir, file_name)


def export_regions_from_layer(orto_path, dxf_path):
    dxf = ezdxf.readfile(dxf_path)
    msp = dxf.modelspace()
    polygons = []

    for entity in msp:
        if entity.dxftype() == 'POLYLINE':
            vertices = [(vertex.dxf.location.x, vertex.dxf.location.y) for vertex in entity.vertices]
            polygons.append(vertices)
        elif entity.dxftype() == 'SPLINE':
            if hasattr(entity, "fit_points"):
                fit_points = entity.fit_points
                vertices = [(point[0], point[1]) for point in fit_points]
            else:
                control_points = entity.control_points
                vertices = [(point[0], point[1]) for point in control_points]
            polygons.append(vertices)
        elif entity.dxftype() == '3DFACE':
            vertices = [
                (entity.dxf.vtx0.x, entity.dxf.vtx0.y),
                (entity.dxf.vtx1.x, entity.dxf.vtx1.y),
                (entity.dxf.vtx2.x, entity.dxf.vtx2.y),
                (entity.dxf.vtx3.x, entity.dxf.vtx3.y)
            ]
            polygons.append(vertices)

    ds = gdal.Open(orto_path)
    gt = ds.GetGeoTransform()

    for idx, poly in enumerate(polygons):
        # Converter coordenadas geográficas para pixels e obter os limites do polígono
        pixel_poly = []
        for coord in poly:
            x, y = coord
            px = int((x - gt[0]) / gt[1])
            py = int((y - gt[3]) / gt[5])
            pixel_poly.append((px, py))

        if not pixel_poly:
            print(f"Aviso: pixel_poly está vazio para polígono {idx+1} no arquivo {dxf_path}")
            continue

        # Obter os limites da região para cortar a imagem
        min_x = min(px for px, py in pixel_poly)
        max_x = max(px for px, py in pixel_poly)
        min_y = min(py for px, py in pixel_poly)
        max_y = max(py for px, py in pixel_poly)

        if min_x == max_x or min_y == max_y:
            print(f"Aviso: Coordenadas inválidas para polígono {idx+1} no arquivo {dxf_path}")
            continue

        # Cortar a imagem TIFF na região do polígono
        region = ds.ReadAsArray(min_x, min_y, max_x - min_x, max_y - min_y)
        region = region.transpose((1, 2, 0))  # Converter para formato (altura, largura, canais)

        # Converter a região cortada para uma imagem PIL e salvar
        image = Image.fromarray(region)
        output_png_path = os.path.join(os.path.dirname(dxf_path), f"{os.path.basename(dxf_path).split('.')[0]}_{idx+1}.png")
        image.save(output_png_path)
        print(f"Imagem salva em {output_png_path}")

if __name__ == "__main__":
    orto_dir = r'D:\Ortofoto_IA\_ORTOFOTO\ESTEIO_META_02'
    dxf_dir = r'C:\Users\0519\Downloads\PISCINA-PAINEL-QE-CF\RESULTADO\R'
    process_directories(orto_dir, dxf_dir)
