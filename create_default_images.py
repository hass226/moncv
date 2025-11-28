from PIL import Image, ImageDraw, ImageFont
import os

def create_default_avatar():
    # Créer une image carrée de 400x400 pixels avec un fond gris clair
    size = 400
    img = Image.new('RGB', (size, size), color='#f0f2f5')
    draw = ImageDraw.Draw(img)
    
    # Dessiner un cercle gris
    circle_margin = 40
    draw.ellipse(
        [(circle_margin, circle_margin), 
         (size - circle_margin, size - circle_margin)], 
        fill='#d1d5db', 
        outline='#9ca3af',
        width=5
    )
    
    # Ajouter une icône d'utilisateur (simplifiée)
    head_radius = 80
    body_height = 100
    
    # Tête
    head_center = (size // 2, size // 2 - 50)
    draw.ellipse(
        [(head_center[0] - head_radius, head_center[1] - head_radius),
         (head_center[0] + head_radius, head_center[1] + head_radius)],
        fill='#9ca3af'
    )
    
    # Corps
    body_top = head_center[1] + head_radius - 10
    body_bottom = body_top + body_height
    body_left = head_center[0] - 60
    body_right = head_center[0] + 60
    
    # Corps principal (triangle arrondi)
    draw.polygon(
        [
            (head_center[0], body_top),
            (body_left, body_bottom - 40),
            (body_right, body_bottom - 40)
        ],
        fill='#9ca3af'
    )
    
    # Bas du corps (arrondi)
    draw.ellipse(
        [(body_left - 10, body_bottom - 80),
         (body_right + 10, body_bottom + 40)],
        fill='#9ca3af'
    )
    
    # Enregistrer l'image
    img.save('/home/nombrehassan/Bureau/moncv (4)/moncv/static/img/default-avatar.png', 'PNG')

def create_default_cover():
    # Créer une image de couverture 1500x500 avec un dégradé
    width, height = 1500, 500
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    
    # Créer un dégradé de bleu
    for y in range(height):
        # Dégradé du bleu clair au bleu foncé
        r = int(30 + (y / height) * 40)
        g = int(64 + (y / height) * 60)
        b = int(175 - (y / height) * 60)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    # Ajouter un motif subtil
    for i in range(0, width, 100):
        for j in range(0, height, 100):
            draw.ellipse(
                [(i, j), (i + 2, j + 2)],
                fill=(255, 255, 255, 20)
            )
    
    # Ajouter un texte au centre
    try:
        # Essayer de charger une police, sinon utiliser la police par défaut
        font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()
    
    text = "Mon Profil"
    text_width = draw.textlength(text, font=font)
    draw.text(
        ((width - text_width) // 2, (height - 40) // 2),
        text,
        fill=(255, 255, 255, 200),
        font=font
    )
    
    # Enregistrer l'image
    img.save('/home/nombrehassan/Bureau/moncv (4)/moncv/static/img/default-cover.jpg', 'JPEG', quality=90)

if __name__ == "__main__":
    # Créer le dossier s'il n'existe pas
    os.makedirs('/home/nombrehassan/Bureau/moncv (4)/moncv/static/img/', exist_ok=True)
    
    print("Création de l'avatar par défaut...")
    create_default_avatar()
    
    print("Création de la bannière par défaut...")
    create_default_cover()
    
    print("Images par défaut créées avec succès !")
