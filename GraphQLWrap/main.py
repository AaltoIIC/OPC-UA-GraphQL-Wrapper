from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware

from starlette.graphql import GraphQLApp
from graphql.execution.executors.asyncio import AsyncioExecutor
from schema import schema

from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from opcuautils import serverList


templates = Jinja2Templates(directory="templates")

app = Starlette(debug=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    '/static',
    StaticFiles(directory='static'),
    name='static'
)
app.mount(
    "/graphql",
    GraphQLApp(schema=schema, executor_class=AsyncioExecutor)
)


@app.route("/")
async def index(request):
    servers = []
    for server in serverList:
        servers.append({"name": server.name})
    return templates.TemplateResponse(
        'index.html', {
            'request': request,
            "servers": servers
        }
    )
