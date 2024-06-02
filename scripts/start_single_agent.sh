
set -e 

# fetch the agent from the local package registry
aea -s fetch $1 --local --alias agent

# go to the new agent
cd agent

# install the agent
# aea -s -v DEBUG install

# create and add a new ethereum key
aea -s generate-key ethereum && aea -s add-key ethereum

# install any agent deps
# aea install

# issue certificates for agent peer-to-peer communications
aea -s issue-certificates

# finally, run the agent
aea -s run

