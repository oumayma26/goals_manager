import sys
import os

# Ajouter la racine du projet au path pour les imports absolus depuis les sous-modules
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)