# Frontend Development Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Project Structure](#project-structure)
4. [Development](#development)
5. [Testing](#testing)

## Introduction
The purpose the frontend loader ui ABCI is to provide an easy means for frontend developers the ability to develop frontends to be served by Agents.

The ABCI frontend loader is designed to not interfer with agent development and applications, but rather to allow services to be augmented with a frontend.

The frontend components are defined as `custom_components` and are loaded by the frontend loader.

## Frontend Specification

The frontnend directory structure is as follows;


```bash
packages/AUTHOR/customs/COMPONENT_NAME/
├── build
│   └── index.html
├── component.yaml
├── __init__.py
└── openapi3_spec.yaml
```

The `component.yaml` file is used to define the frontend component and its dependencies.

The `openapi3_spec.yaml` file is used to define the openapi3 spec for the frontend component.

The `build` directory contains the compiled frontend component.

### Component.yaml

An example of a `component.yaml` file is as follows;

```yaml
name: trader_ui
author: tatha
version: 0.1.0
type: custom
description: Custom UI representing a user interface for the trader skill.
license: Apache-2.0
aea_version: '>=1.0.0, <2.0.0'
fingerprint:
  __init__.py: bafybeih4oyyzgld4vqtbub6zrcrrfofbhmhbr37rvoxuhzchn3bhhjs7za
  build/index.html: bafybeidtlac2qbn6oohhyyuvbwz36dqxofyiv7s4tsipwbrsl5mnbn65ga
  openapi3_spec.yaml: bafybeiagdbghwj4t4o7uctojvtkjp7i6zxpwu6dltjsawcaeuteyipftty
fingerprint_ignore_patterns: []
dependencies: {}
api_spec: open_api3_spec.yaml
frontend_dir: build
```

Notice the extra fields `api_spec` and `frontend_dir` which are used to define the openapi3 spec and the frontend directory respectively.

### Openapi3 Spec
The framework uses the openapi3 spec to define the API for the frontend component.

An example of an `openapi3_spec.yaml` file is as follows;

```yaml
openapi: 3.0.0
info:
  title: Pandora API
  description: Allows interactions with Autonomous Agents
  version: 0.1.0
servers:
  - url: http://0.0.0.0:5555
paths:
  /:
    get:
      summary: Returns the main HTML page
      responses:
        '200':
          description: HTML response
          content:
            text/html:
              schema:
                type: string
  api/agent-info:
    get:
      summary: Returns the agent's state and info
      responses:
        '200':
          description: A Json response
          content:
            application/json:
              schema:
                type: object
                properties:
                  service-id:
                    type: string
                  safe-address:
                    type: string
                  agent-address:
                    type: string
                  agent-status:
                    type: string
```

The openapi3 spec is used to define the API for the frontend component.

Note: Future extension will include the ability to define `handlers` for the frontend apis.


### Build
The `build` directory contains the compiled frontend code generated from Javascript frameworks like React, Angular, Vue etc.

For example, the `build` directory for a React app would look like this;

```bash
packages/AUTHOR/customs/COMPONENT_NAME
`
├── build
│   ├── asset-manifest.json
│   ├── favicon.ico
│   ├── index.html
│   ├── logo192.png
│   ├── logo512.png
```

### Current Features.

- Generate routes from the `build` directory.
- enable `API` routes from the `openapi3_spec.yaml` file.
- ABCI spec with healthcheck for the served frontend.
- Independant Protocols and servers for the frontend components meaning no interaction with core skills.


### Future Features.

- Extend to allow websockets.
- Extend to allow custom `handlers` for the frontend apis.