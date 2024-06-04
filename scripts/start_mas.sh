#! /bin/bash
# Start the MAS service.
set -e

echo "Using autonomy version: $(autonomy --version)"

# we check if the service alias is already used
# if it is, we hard exit
if [ -d "service" ]; then
    echo "Service $1 already exists at path ./service"
    exit 1
fi
echo "-----------------------------"
echo "Starting service $1"

# if the key path is not set, we hard exit
if [ -z "$MAS_KEYPATH" ]; then
    export MAS_KEYPATH="keys.json"
fi

echo "-----------------------------"
echo "Using keys: $MAS_KEYPATH"

export MAS_ADDRESS=$(echo -n $(cat $MAS_KEYPATH | jq '.[].address' -r))

echo "Using Address: $MAS_ADDRESS"


export ALL_PARTICIPANTS="[\"$MAS_ADDRESS\"]"

# if the service name is not set, we hard exit
if [ -z "$1" ]; then
    echo "Service name is not set!"
    exit 1
fi

autonomy fetch --service $1 --local --alias service
cd service 
autonomy build-image 
autonomy deploy build $MAS_KEYPATH --n 1 -ltm

echo "-----------------------------"
echo "Service $1 built!"


# Function to add a volume to a service in a Docker Compose file
add_volume_to_service() {
    local compose_file="$1"
    local service_name="$2"
    local volume_name="$3"
    local volume_path="$4"

    # Check if the Docker Compose file exists
    if [ ! -f "$compose_file" ]; then
        echo "Docker Compose file '$compose_file' not found."
        return 1
    fi

    # Check if the service exists in the Docker Compose file
    if ! grep -q "^[[:space:]]*${service_name}:" "$compose_file"; then
        echo "Service '$service_name' not found in '$compose_file'."
        return 1
    fi

    if grep -q "^[[:space:]]*volumes:" "$compose_file"; then
        awk -v volume_path="$volume_path" -v volume_name="$volume_name" '
            /^ *volumes:/ {
                found_volumes = 1
                print
                print "      - " volume_path ":" volume_name ":Z"
                next
            }
            1
        ' "$compose_file" > temp_compose_file
    else
        awk -v service_name="$service_name" -v volume_path="$volume_path" -v volume_name="$volume_name" '
            /^ *'"$service_name"':/ {
                found_service = 1
                print
                print "    volumes:"
                print "      - " volume_path ":" volume_name ":Z"
                next
            }
            /^ *$/ && found_service == 1 {
                print "    volumes:"
                print "      - " volume_path ":" volume_name ":Z"
                found_service = 0
            }
            1
        ' "$compose_file" > temp_compose_file
    fi

    mv temp_compose_file "$compose_file"
}





echo "Starting service $1"

store="../.trader_runner"
mkdir -p $store
add_volume_to_service "$PWD/abci_build/docker-compose.yaml" "trader_abci_0" "/data/" "$PWD/$store/"

cd abci_build && \
    sudo chown -R $USER:$USER ./ && \
    docker-compose up -d --force-recreate
echo "Service $1 started!"
