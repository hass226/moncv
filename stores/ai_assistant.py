"""
🤖 Assistant IA pour MYMEDAGA
Génération de descriptions, images, traductions, prix optimaux, etc.
"""

import os
from django.conf import settings
from .models import AIRequest, Product
from django.utils import timezone
import json

# Configuration OpenAI (utiliser des variables d'environnement en production)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# Import OpenAI seulement si disponible
try:
    import openai
    if OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
except ImportError:
    openai = None


def generate_product_description(product_name, category=None, price=None, language='fr'):
    """
    Génère une description de produit optimisée pour la vente
    """
    prompt = f"""Tu es un expert en marketing e-commerce. 
    Génère une description de produit accrocheuse et persuasive pour:
    - Nom: {product_name}
    - Catégorie: {category or 'Non spécifiée'}
    - Prix: {price or 'Non spécifié'}
    
    La description doit:
    1. Être accrocheuse et engageante
    2. Mettre en avant les bénéfices
    3. Utiliser des mots-clés SEO
    4. Être en {language}
    5. Faire entre 100-200 mots
    
    Description:"""
    
    if not openai:
        return {
            'success': False,
            'error': 'OpenAI n\'est pas installé. Installez-le avec: pip install openai'
        }
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un expert en marketing e-commerce spécialisé dans la rédaction de descriptions de produits."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        description = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens
        
        return {
            'success': True,
            'description': description,
            'tokens_used': tokens_used
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def suggest_optimal_price(product_name, category, cost_price=None, competitor_prices=None):
    """
    Suggère un prix optimal basé sur le marché et la stratégie
    """
    competitor_info = ""
    if competitor_prices:
        avg_competitor = sum(competitor_prices) / len(competitor_prices)
        competitor_info = f"Prix moyens des concurrents: {avg_competitor}"
    
    cost_info = f"Prix de revient: {cost_price}" if cost_price else "Prix de revient: Non spécifié"
    
    prompt = f"""Tu es un expert en pricing e-commerce.
    Suggère un prix optimal pour:
    - Produit: {product_name}
    - Catégorie: {category}
    - {cost_info}
    - {competitor_info}
    
    Fournis:
    1. Prix suggéré
    2. Justification (stratégie)
    3. Marge estimée
    4. Positionnement (premium, moyen, économique)
    
    Réponse en format JSON: {{"price": X, "strategy": "...", "margin": X, "positioning": "..."}}"""
    
    if not openai:
        return {
            'success': False,
            'error': 'OpenAI n\'est pas installé. Installez-le avec: pip install openai'
        }
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un expert en pricing et stratégie de prix pour e-commerce."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.5
        )
        
        result_text = response.choices[0].message.content.strip()
        # Essayer de parser le JSON
        try:
            result = json.loads(result_text)
        except:
            result = {"raw_response": result_text}
        
        return {
            'success': True,
            'result': result,
            'tokens_used': response.usage.total_tokens
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def generate_product_tags(product_name, description, category):
    """
    Génère des tags/étiquettes optimisés pour un produit
    """
    prompt = f"""Génère 5-10 tags pertinents pour ce produit:
    - Nom: {product_name}
    - Description: {description[:200]}
    - Catégorie: {category}
    
    Les tags doivent être:
    1. Pertinents et descriptifs
    2. Optimisés pour la recherche
    3. En français
    4. Séparés par des virgules
    
    Tags:"""
    
    if not openai:
        return {
            'success': False,
            'error': 'OpenAI n\'est pas installé. Installez-le avec: pip install openai'
        }
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un expert en SEO et tagging de produits e-commerce."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        tags_text = response.choices[0].message.content.strip()
        tags = [tag.strip() for tag in tags_text.split(',')]
        
        return {
            'success': True,
            'tags': tags,
            'tokens_used': response.usage.total_tokens
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def translate_text(text, target_language='en', source_language='fr'):
    """
    Traduit un texte dans une autre langue
    """
    prompt = f"""Traduis ce texte de {source_language} vers {target_language}:
    
    {text}
    
    Traduction:"""
    
    if not openai:
        return {
            'success': False,
            'error': 'OpenAI n\'est pas installé. Installez-le avec: pip install openai'
        }
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"Tu es un traducteur professionnel de {source_language} vers {target_language}."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        translation = response.choices[0].message.content.strip()
        
        return {
            'success': True,
            'translation': translation,
            'tokens_used': response.usage.total_tokens
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def generate_marketing_text(product_name, product_type='product'):
    """
    Génère un texte marketing accrocheur
    """
    prompt = f"""Crée un texte marketing court et accrocheur (50-100 mots) pour:
    - {product_type}: {product_name}
    
    Le texte doit:
    1. Être accrocheur et émotionnel
    2. Mettre en avant les bénéfices
    3. Inclure un call-to-action
    4. Être adapté aux réseaux sociaux
    
    Texte marketing:"""
    
    if not openai:
        return {
            'success': False,
            'error': 'OpenAI n\'est pas installé. Installez-le avec: pip install openai'
        }
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un expert en copywriting et marketing digital."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.8
        )
        
        marketing_text = response.choices[0].message.content.strip()
        
        return {
            'success': True,
            'marketing_text': marketing_text,
            'tokens_used': response.usage.total_tokens
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def optimize_product_title(current_title, category):
    """
    Optimise un titre de produit pour le SEO et l'engagement
    """
    prompt = f"""Optimise ce titre de produit pour:
    1. Le SEO (mots-clés pertinents)
    2. L'engagement (accrocheur)
    3. La clarté
    
    Titre actuel: {current_title}
    Catégorie: {category}
    
    Fournis 3 variantes optimisées (une par ligne):"""
    
    if not openai:
        return {
            'success': False,
            'error': 'OpenAI n\'est pas installé. Installez-le avec: pip install openai'
        }
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un expert en SEO et optimisation de titres pour e-commerce."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        titles_text = response.choices[0].message.content.strip()
        titles = [t.strip() for t in titles_text.split('\n') if t.strip()]
        
        return {
            'success': True,
            'titles': titles,
            'tokens_used': response.usage.total_tokens
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def process_ai_request(ai_request):
    """
    Traite une requête IA et met à jour le modèle
    """
    ai_request.status = 'processing'
    ai_request.save()
    
    try:
        result = None
        
        if ai_request.request_type == 'product_description':
            result = generate_product_description(
                ai_request.input_text or (ai_request.product.name if ai_request.product else ''),
                category=ai_request.product.category.name if ai_request.product and ai_request.product.category else None,
                price=str(ai_request.product.price) if ai_request.product else None,
                language=ai_request.input_language
            )
            if result['success']:
                ai_request.output_text = result['description']
                ai_request.tokens_used = result.get('tokens_used', 0)
        
        elif ai_request.request_type == 'pricing':
            result = suggest_optimal_price(
                ai_request.input_text or (ai_request.product.name if ai_request.product else ''),
                category=ai_request.product.category.name if ai_request.product and ai_request.product.category else '',
                cost_price=None  # À implémenter si disponible
            )
            if result['success']:
                ai_request.metadata = result.get('result', {})
                ai_request.tokens_used = result.get('tokens_used', 0)
        
        elif ai_request.request_type == 'tags':
            result = generate_product_tags(
                ai_request.input_text or (ai_request.product.name if ai_request.product else ''),
                description=ai_request.product.description if ai_request.product else '',
                category=ai_request.product.category.name if ai_request.product and ai_request.product.category else ''
            )
            if result['success']:
                ai_request.metadata = {'tags': result['tags']}
                ai_request.output_text = ', '.join(result['tags'])
                ai_request.tokens_used = result.get('tokens_used', 0)
        
        elif ai_request.request_type == 'translation':
            result = translate_text(
                ai_request.input_text,
                target_language=ai_request.target_language,
                source_language=ai_request.input_language
            )
            if result['success']:
                ai_request.output_text = result['translation']
                ai_request.tokens_used = result.get('tokens_used', 0)
        
        elif ai_request.request_type == 'marketing_text':
            result = generate_marketing_text(
                ai_request.input_text or (ai_request.product.name if ai_request.product else ''),
                product_type='produit'
            )
            if result['success']:
                ai_request.output_text = result['marketing_text']
                ai_request.tokens_used = result.get('tokens_used', 0)
        
        elif ai_request.request_type == 'title':
            result = optimize_product_title(
                ai_request.input_text or (ai_request.product.name if ai_request.product else ''),
                category=ai_request.product.category.name if ai_request.product and ai_request.product.category else ''
            )
            if result['success']:
                ai_request.metadata = {'titles': result['titles']}
                ai_request.output_text = result['titles'][0] if result['titles'] else ''
                ai_request.tokens_used = result.get('tokens_used', 0)
        
        if result and result.get('success'):
            ai_request.status = 'completed'
            ai_request.completed_at = timezone.now()
            # Calculer le coût (approximatif: $0.002 per 1K tokens pour GPT-3.5)
            ai_request.cost = (ai_request.tokens_used / 1000) * 0.002
        else:
            ai_request.status = 'failed'
            ai_request.error_message = result.get('error', 'Erreur inconnue') if result else 'Aucun résultat'
        
        ai_request.save()
        return ai_request
        
    except Exception as e:
        ai_request.status = 'failed'
        ai_request.error_message = str(e)
        ai_request.save()
        return ai_request

