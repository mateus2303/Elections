# Motor Python compartilhado

O motor contém a leitura da base, padronização, validação, pesos, agregação, probabilidade, publicação e geração dos gráficos. A separação metodológica ocorre na chamada:

- `--model a`: `legacy-baseline-1.0`, Modelo A oficial;
- `--model b`: `model-b-candidate-0.1`, Modelo B experimental.

Os módulos específicos ficam no mesmo motor para evitar duas cópias divergentes. `weighting.py` contém o baseline e `model_b.py` contém as regras adicionais do candidato; `presentation.py` gera os dois pacotes de gráficos e planilhas sem fixar nomes de adversários.

Para instalar o motor diretamente:

```powershell
python -m pip install -e .
```
