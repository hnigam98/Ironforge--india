# IRONFORGE V14 — Diet Goals Update

This package is based on the supplied IRONFORGE Manual UPI V13 Django deployment bundle. The frontend `frontend/index.html` has been updated to V14 with new goals shown only in the **Only Diet** service.

## New diet goal options
- Fat loss
- Muscle gain
- Healthy weight gain
- Maintain weight
- Body recomposition
- Micronutrient-rich diet (vitamins)
- Mineral-rich diet
- High-protein diet
- Sports performance and recovery
- Gut health and fiber-rich diet
- Budget-friendly balanced diet

Users can also select additional nutrition priorities such as iron-rich foods, calcium-rich foods, fiber, omega-3 sources, hydration/electrolytes, more vegetables and fruit, and affordable protein foods. Selected goals are included in the generated diet plan.

## Deploy
Use this folder as the project root. Follow `README.md` and `DEPLOYMENT_CHECKLIST.md`; configure production environment variables and database before deploying. Keep your production secrets out of the package/repository.

## Validation
The updated HTML inline JavaScript was syntax-checked with Node.js. Django deployment checks still need to be run in an environment with the package dependencies and configured environment variables/database.
