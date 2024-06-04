
set -e

function gv(){
    echo "Minting $1 $2"

    rm mints/$2.json || true
    adev metadata generate . $1 $2
    adev -v metadata validate mints/$2.json
}


# gv skill/eightballer/ui_loader_abci/0.1.0 12 > /dev/null
# gv custom/eightballer/simple_html/0.1.0 13 > /dev/null
# gv custom/eightballer/simple_react/0.1.0 14 > /dev/null

# gv agent/eightballer/trader/0.1.0 15
gv service/eightballer/trader/0.1.0 16