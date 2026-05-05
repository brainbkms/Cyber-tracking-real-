# 🛡️ Cyber-Tracking-Real v5.0

**Système de détection d'intrusion avec IA prédictive, localisation GPS et scan réseau temps réel**

[![GitHub stars](https://img.shields.io/github/stars/cybertrack/cyber-tracking-real)](https://github.com/cybertrack/cyber-tracking-real)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Firebase](https://img.shields.io/badge/Firebase-Cloud-orange)](https://firebase.google.com)
[![GitHub Pages](https://img.shields.io/badge/GitHub-Pages-blue)](https://pages.github.com)

## ✨ Fonctionnalités

| Fonctionnalité | Description | Statut |
|----------------|-------------|--------|
| 📍 **Localisation GPS** | Position géographique précise en temps réel | ✅ |
| 🌐 **Scan réseau** | IP publique, pays, FAI, détection VPN/Proxy | ✅ |
| 🚨 **Détection intrusion** | Alerte immédiate avec localisation | ✅ |
| 🧠 **IA prédictive** | Analyse comportementale et scoring risque | ✅ |
| 📊 **Dashboard IA** | Graphique prédictif des menaces | ✅ |
| ☁️ **Cloud Firebase** | Sauvegarde automatique des intrusions | ✅ |
| 📥 **Export données** | JSON avec analyses IA | ✅ |
| 📱 **Responsive** | Fonctionne sur mobile, tablette, desktop | ✅ |

## 🎯 IA Prédictive - Comment ça marche

Le système utilise un modèle d'analyse multi-facteurs :

```python
# Facteurs analysés par l'IA
risk_factors = {
    "Horaire": "Plus de risques la nuit (22h-5h)",
    "VPN/Proxy": "+30% de risque si détecté",
    "Historique": "Score basé sur les intrusions passées",
    "Changement IP": "Anomalie potentielle",
    "Weekend": "Activité suspecte majorée"
}
