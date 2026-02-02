
from decimal import Decimal, ROUND_HALF_UP

def calculer_irsa_brut(rni):
    # On s'assure de travailler en Decimal
    rni = Decimal(str(rni))
    impot = Decimal('0.00')

    # Tranche 1 : 0 à 350k (0%) -> On ne fait rien
    
    # Tranche 2 : 350.001 à 400.000 (5%)
    if rni > 350000:
        base = min(rni, Decimal('400000')) - 350000
        impot += base * Decimal('0.05')

    # Tranche 3 : 400.001 à 500.000 (10%)
    if rni > 400000:
        base = min(rni, Decimal('500000')) - 400000
        impot += base * Decimal('0.10')

    # Tranche 4 : 500.001 à 600.000 (15%)
    if rni > 500000:
        base = min(rni, Decimal('600000')) - 500000
        impot += base * Decimal('0.15')

    # Tranche 5 : 600.001 à 4.000.000 (20%)
    if rni > 600000:
        base = min(rni, Decimal('4000000')) - 600000
        impot += base * Decimal('0.20')

    # Tranche 6 : > 4.000.000 (25%)
    if rni > 4000000:
        base = rni - 4000000
        impot += base * Decimal('0.25')

    # Le minimum fiscal est de 3000 Ar si le RNI > 350 000
    if rni > 350000:
        return max(impot, Decimal('3000.00')).quantize(Decimal('1.00'), rounding=ROUND_HALF_UP)
    
    return Decimal('0.00') # Pour les revenus inférieurs à 350k
def calculer_reduction_charge(nb_personnes):
    """Réduction d'impôt de 2.000 Ar par personne à charge"""
    return Decimal(str(nb_personnes * 2000))