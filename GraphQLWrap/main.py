from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware

from starlette.graphql import GraphQLApp
from graphql.execution.executors.asyncio import AsyncioExecutor
from schema import schema

from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from opcuautils import serverList


templates = Jinja2Templates(directory="templates")

app = Starlette(debug=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount("/graphql", GraphQLApp(schema=schema, executor_class=AsyncioExecutor))

@app.route("/")
async def index(request):
    servers = []
    for server in serverList:
        servers.append({"name": server.name})
    #return render_template("index.html", servers=servers, url=request.url)
    return templates.TemplateResponse('index.html', {'request': request, "servers": servers})

""" app = Starlette(debug=True, routes=[
    Route("/", index),
    Route("/graphql", GraphQLApp(schema=schema, executor_class=AsyncioExecutor)),
    Mount("/static", StaticFiles(directory="static"), name="static")
])


templates = Jinja2Templates(directory='templates')

app = Starlette(debug=True)
app.mount('/static', StaticFiles(directory='statics'), name='static')


@app.route('/')
async def homepage(request):
    template = "index.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context) """