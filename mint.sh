
set -e

function gv(){
    echo "Minting $1 $2"

    rm mints/$2.json || true
    adev metadata generate . $1 $2
    adev -v metadata validate mints/$2.json
}


gv skill/eightballer/ui_loader_abci/0.1.0 12
gv agent/valory/trader/0.1.0 13


