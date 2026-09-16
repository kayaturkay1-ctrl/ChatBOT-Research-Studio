# Streamlit Community Cloud Deployment

## Repo root
- app.py
- engine.py
- frontend.py
- requirements.txt
- default.pdf  <-- kendi gerçek varsayılan PDF dosyanızı buraya ekleyin
- .streamlit/config.toml

## Community Cloud
1. GitHub'a bu klasörün içeriğini yükleyin.
2. https://share.streamlit.io adresinde Create app seçin.
3. Repository ve main branch'i seçin.
4. Entrypoint: app.py
5. Advanced settings > Python: 3.12
6. Secrets alanına `.streamlit/secrets.example.toml` içeriğini gerçek OPENAI_API_KEY ile girin.
7. Deploy.

