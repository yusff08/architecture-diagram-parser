from PIL import Image, ImageDraw, ImageFont
import os

def generate_reference_diagram(output_path: str = "tests/fixtures/test_diagram.png") -> str:
    """
    Génère un diagramme de cas d'utilisation UML de référence pour les tests
    avec acteurs, cas d'utilisation (ellipses) et dépendances include/extend.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    width, height = 600, 400
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Cadre du système UML
    draw.rectangle([50, 30, 550, 370], outline=(70, 70, 70), width=2)
    draw.text((60, 40), "Système: Gestion Bancaire", fill=(30, 30, 30))
    
    # Acteur "Client" (représentation simple)
    # Tête
    draw.ellipse([80, 100, 110, 130], outline=(0, 0, 0), width=2)
    # Corps
    draw.line([95, 130, 95, 170], fill=(0, 0, 0), width=2)
    # Bras
    draw.line([75, 145, 115, 145], fill=(0, 0, 0), width=2)
    # Jambes
    draw.line([95, 170, 80, 200], fill=(0, 0, 0), width=2)
    draw.line([95, 170, 110, 200], fill=(0, 0, 0), width=2)
    draw.text((80, 210), "Client", fill=(0, 0, 0))
    
    # Cas d'utilisation 1 : S'authentifier
    draw.ellipse([220, 90, 380, 150], outline=(30, 80, 180), width=2, fill=(240, 245, 255))
    draw.text((250, 110), "S'authentifier", fill=(20, 20, 20))
    
    # Cas d'utilisation 2 : Consulter Solde
    draw.ellipse([220, 220, 380, 280], outline=(30, 80, 180), width=2, fill=(240, 245, 255))
    draw.text((245, 240), "Consulter Solde", fill=(20, 20, 20))
    
    # Cas d'utilisation 3 : Valider Biometrie (<<extend>>)
    draw.ellipse([420, 150, 540, 210], outline=(30, 80, 180), width=2, fill=(240, 245, 255))
    draw.text((435, 170), "Biométrie", fill=(20, 20, 20))
    
    # Lignes d'association
    draw.line([115, 145, 220, 120], fill=(50, 50, 50), width=2)
    draw.line([115, 145, 220, 250], fill=(50, 50, 50), width=2)
    
    # Relation <<include>>
    draw.line([300, 220, 300, 150], fill=(120, 120, 120), width=1)
    draw.text((305, 180), "<<include>>", fill=(100, 100, 100))
    
    # Relation <<extend>>
    draw.line([380, 120, 420, 160], fill=(120, 120, 120), width=1)
    draw.text((370, 140), "<<extend>>", fill=(100, 100, 100))
    
    image.save(output_path, "PNG")
    return output_path

if __name__ == "__main__":
    generate_reference_diagram()
    print("Fixture test_diagram.png générée avec succès.")
