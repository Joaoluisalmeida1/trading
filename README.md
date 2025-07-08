# Projeto de Trading

Este repositorio contem um esqueleto para desenvolvimento de estrategias de trading algor\u00edtico utilizando Python.

## Objetivo

Fornecer uma base simples para estudos e prototipa\u00e7\u00e3o de sistemas de trading, incluindo m\u00f3dulos de comunica\u00e7\u00e3o com corretoras, backtesting e dashboards.

## Requisitos de Ambiente

- Python 3
- [virtualenv](https://virtualenv.pypa.io/en/latest/)

Recomenda-se criar um ambiente virtual para isolar as depend\u00eancias do projeto.

```bash
python3 -m venv venv
source venv/bin/activate
```

## Instala\u00e7\u00e3o de Depend\u00eancias

Com o ambiente virtual ativado, instale os pacotes necess\u00e1rios executando:

```bash
pip install -r requirements.txt
```

## Configura\u00e7\u00e3o do .env

O projeto utiliza um arquivo `.env` na raiz para armazenar vari\u00e1veis de ambiente sens\u00edveis, como chaves de API. Crie ou edite esse arquivo e defina as vari\u00e1veis conforme sua necessidade, por exemplo:

```bash
API_KEY=seu_token
API_SECRET=sua_senha
```

Salve o arquivo antes de iniciar a aplica\u00e7\u00e3o.

