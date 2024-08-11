import logging
from pathlib import Path, PosixPath

import uvicorn
from fastapi import FastAPI, Request, Query, HTTPException, UploadFile, Form, File
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)

# 屏蔽 urllib3 的日志输出
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
# 屏蔽 requests 的日志输出
logging.getLogger("requests").setLevel(logging.CRITICAL)
# 屏蔽 http.client 的日志输出
logging.getLogger("http.client").setLevel(logging.CRITICAL)

app = FastAPI(
    title='网狗盘',
    summary='python版',
    description='文件管理器',
    version='1.0',
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/js", StaticFiles(directory="static/js"), name="js")
app.mount("/css", StaticFiles(directory="static/css"), name="css")
app.mount("/img", StaticFiles(directory="static/img"), name="img")
app.mount("/fonts", StaticFiles(directory="static/fonts"), name="fonts")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=FileResponse)
async def index(request: Request):
    file_path = os.path.join("templates", "index.html")
    return FileResponse(file_path)


def _root_path():
    if os.getenv('root_path'):
        root_path = os.getenv('root_path')
    else:
        root_path = '/Users/liuyuhua/Downloads'
    return root_path


def path_with_root(path) -> str:
    root_path = _root_path()
    if isinstance(path, str):
        if path.startswith('/'):
            return f'{root_path}/{path[1:]}'
        return f'{root_path}/{path}'
    elif isinstance(path, PosixPath):
        real_path = str(path)
        return real_path.replace(root_path, '')
    else:
        raise BaseException('错误的path参数类型,必须是str或者PosixPath类型')


@app.get("/list")
async def list_files(path: str | None = Query('/', alias='path'), ):
    try:
        _path = path_with_root(path)
        real_path = Path(_path)
        files = []
        for item in real_path.iterdir():
            if item.is_dir():
                files.append({
                    "name": item.name,
                    "path": f'{path_with_root(item)}/',
                    "file_type": 'directory'
                })
            elif item.is_file():
                files.append({
                    "name": item.name,
                    "path": path_with_root(item),
                    "file_type": 'file'
                })
        files = sorted(files, key=lambda x: 0 if x['file_type'] == 'directory' else 1)
        return files
    except BaseException as e:
        logging.exception(e)
        return JSONResponse(content={"detail": str(e)}, status_code=500)


@app.post("/upload")
async def upload_files(path: str = Form(alias='path'), files: list[UploadFile] = File(alias='files[]')):
    try:
        real_path = Path(path_with_root(path))
        saved_files = []
        for file in files:
            file_location = real_path.joinpath(file.filename)
            with open(file_location, "wb") as f:
                f.write(await file.read())
            saved_files.append(file.filename)
        return JSONResponse(content={"filenames": saved_files}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"detail": str(e)}, status_code=500)


if __name__ == "__main__":
    import os

    os.environ["http_proxy"] = ""
    os.environ["https_proxy"] = ""
    logging.info('启动pydog助手: http://127.0.0.1:8007')
    logging.info('API文档: http://127.0.0.1:8007/docs')
    uvicorn.run(app, host="0.0.0.0", port=8007, timeout_keep_alive=60, reload=False)
