# To do

pull and run the agent as docker in a one liner.

git clone git@github.com:8ball030/trader.git && \
    cd trader && \
    poetry install && \
    poetry run autonomy packages sync && \
    poetry run autonomy generate-key ethereum -n 1 && \
    poetry run bash scripts/start_mas.sh valory/trader

