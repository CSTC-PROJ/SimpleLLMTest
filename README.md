# Locally Hosted LLM – Test
## Purpose
Having come to the realisation that large language models (LLMs) and AI, including Agentic AI, are unlikely to follow the same path as blockchain (where its potential remains underutilised) — I decided to experiment with an LLM to set up a simple query system.  While this approach does not fully leverage the capabilities of LLMs, it has given me valuable insights in to how interactions occur.

Gartner Hypecycle: https://emt.gartnerweb.com/ngw/globalassets/en/articles/infographics/hype-cycle-for-artificial-intelligence-2024.jpg

### Note that this solution lacks any security measures (e.g. HTTPS and data-at-rest protection) – I do not recommend using it as is for anything other than testing

### i take no credit for the coding, I’m an orchestrator not a developer – you can thank co-pilot for the awesome/equally sloppy coding** **😊**

# System Specifications
This solution was performed on a low powered VM with an equally unimpressive CPU with the following specifications:

- CPU: 4 Core Ryzen 6800u (Low Power)
- Memory: 8GB (Regularly Maxed Out)
- Storage: 200GB (only uses ~20gb, no swap file)

Software
- Ubuntu Server 24.04
- Ollama
- Python3
- NodeJS 22.x

# Installation
## Ollama - https://ollama.com/
Ollama can be installed as a single line command, which results in not only LLM runtime being installed, but also the respective systemd service entries are created too meaning it doesn’t require any work to start the service.

```bash
curl -fsSL https://ollama.com/install.sh | sh
```
![image](https://github.com/user-attachments/assets/77940629-a474-4013-97f5-d685e7eb5335)

Once installed

```bash
Ollama
```

This will present the available commands.

*Notes*
- Ollama is exposed by default to Localhost – if you wish to call the Ollama API from an external source directly, then you will need to set the environment within the systemd service entry.

```bash
sudo nano /etc/systemd/system/ollama.service
```

add the following entry to the Service Section

```bash
Environment="OLLAMA_HOST=0.0.0.0"
```

and then

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
sudo systemctl status Ollama
```


## Model
For the model, I used Gemma:2b.  While there are no doubt better models out there (that I haven’t yet tested), following research – I looked to find something with a good parameter size and a reasonable memory requirement.
- https://deepwiki.com/ollama/ollama/1.2-system-requirements](https://deepwiki.com/ollama/ollama/1.2-system-requirements
- https://mljourney.com/top-10-smallest-llm-to-run-locally/](https://mljourney.com/top-10-smallest-llm-to-run-locally/

To install the model.

```bash
ollama pull gemma:2b
```


Test the model installed and is available.

```bash
ollama run gemma:2b
```

Check the Ollama API server is up

```bash
curl -X POST http://localhost:11434/api/generate \
-H "Content-Type: application/json" \
-d '{
"model": "gemma:2b",
"prompt": "What is the capital of France?",
"stream": false
}'
```

This is the basics of running the LLM locally.

## Observations
- Gemma is fine, probably not the most optimised but seems reasonable enough.  I don’t believe Ollama tracks session history and so context is not there meaning each question is a new question.
- If you have multiple models installed, then passing the relevant model in the curl request should target that model.

  
## Guardrail
The purpose of the guardrail is to augment the inbuilt safety controls in the gemma:2b model and ensure that any additional elements are prevented from being passed to or from the LLM.  To do this, I’ve used a vectorised and embedding approach that mathematically calculates the distance between 2 vectors to determine their similarity.  I don’t understand fully how this works at the moment but I may update with some links later.  I’ve tried with Milvus [https://milvus.io/](https://milvus.io/) and ChromaDB [https://docs.trychroma.com](https://docs.trychroma.com).  Both were a pain to get working and I spent several hours, before settling on FAISS [https://faiss.ai/](https://faiss.ai/).

FAISS resides in memory meaning it loses everything when it closes, but this can be rectified by writing any stored embeddings to disk each time a new one is added.  To properly embed anything text passed, [https://www.sbert.net/](https://www.sbert.net/) is used for transforming the words or sentences.  Again this is beyond me at this time.

The Guardrail “service” is an API that runs FAISS and provides an interaction layer.  It’s all Python3 based.

Pip3 (python package installer) is not available by default so install it if required.

```bash
sudo apt-get install python3-pip
```

There are a number of packages required for the API which need installing.

```bash
pip install faiss-cpu sentence-transformers numpy flask flask-cors --break-system-packages your-package
```

“break system packages” may not be required, but a number of errors were thrown and it was this or using venv (and I don’t know venv)

Several warnings get thrown.  I don’t know if they have any impact but to resolve this I added the following just to be sure.

```bash
echo 'export PATH=$HOME/.local/bin:$PATH'  >>  ~/.bashrc
source ~/.bashrc
echo 'export PATH=$HOME/.local/bin:$PATH'  >>  ~/.zshrc
source ~/.zshrc
```

Python is now ready to host the flask application that will allow you to create guard rails.  In advance – I know I’m using POST everywhere but I’m not that precious about restful principles.

### Source code for the python app and the NodeJS server can be found here:** [**https://github.com/CSTC-PROJ/SimpleLLMTest**](https://github.com/CSTC-PROJ/SimpleLLMTest)

As there are 2 applications to run in this solution (Python and Node) you can either login to 2 separate ssh sessions and run each separately or run Python in the background.

```bash
python3 guardrail.py
```

** or **

```bash
nohup /usr/bin/python3 guardrail.py > flask.log 2>&1  &
```

view logs with

```bash
tail -f flask.log
```

terminate Python API with

```bash
kill -9 $(pgrep -f 'python3 guardrail.py')
```

**Test the API**

To add an embedding…
```bash
curl -X POST http://localhost:8080/add-embedding -H "Content-Type: application/json" -d "{\"text\": \"harmful intent\"}"
```

To show all embeddings currently…
```
curl  http://localhost:8080/show-all
```

To Query against the embeddings…

```bash
curl -X POST http://localhost:8080/query-embedding -H "Content-Type: application/json" -d "{\"query\": \"harm\"}"
```

To delete a single embedding…
```bash
curl -X POST http://localhost:8080/delete-text -H "Content-Type: application/json" -d "{\"text\": \"harmful intent\"}"
```

To delete all embeddings…

```bash
curl -X POST http://localhost:8080/delete-all
```

## Web Application Server
The Web Application exists purely to facilitate the flow of consumer to guardrail to LLM.  While it’s possible to just interact natively with the Guard Rail and Ollama through a bash script, there’s little fun in that.  The Web Application is a simple NodeJS Express with Handlebars that supports calls to both in an orderly fashion.  Again, this could have been done from a simple HTML page on a Python http server, but I wanted to control access to the LLM to be explicitly after the Guardrail.

**Node JS Installation**
NodeJS application installation from the apt repository is by default very out of date.  This application will not run on the out of the box version and has been tested on node 20+
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash –
sudo apt install -y nodejs
```

In the directory cloned earlier

```bash
npm install
```

change the IP address in the ``admin.hanlebars`` to the IP address of the hosting server – this is because the guardrail page calls the API directly and not through the node server.

```
node server.js
```

There are 2 pages that can be accessed.  The home page on the left and admin on the right.

Admin
- Allows the creation of, removal of, and testing against guardrails.  This is quicker than trying the main chat to match a guardrail

The Chat page
- allows uploading text files for querying
- basic chats
- will show any failure against custom guardrails on the left (both input to the LLM and output from) - show chat outputs on the right

**Limitations**
- no context/memory of a chat – forms a standalone query engine only.  To include past context either this would need to be string built to send the entire history each time or there may be a setting I’ve not stumbled upon yet.
- No access to internet sources so limited to the model in use
- If you reference “tell me about the file” then it doesn’t understand it’s received a file as it’s all sent as text.
- Guardrails are subject to mismatches and so tolerances may need to be adjusted in the code – see the respective variable – set at 0.5 by default.
