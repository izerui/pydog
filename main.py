import logging
import shutil
import tempfile
from pathlib import Path, PosixPath

import uvicorn
from fastapi import FastAPI, Request, Query, UploadFile, Form, File, BackgroundTasks, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette import status
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

security = HTTPBasic()


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = "admin"
    correct_password = "admin.123"
    if os.getenv('username'):
        correct_username = os.getenv('username')
    if os.getenv('password'):
        correct_password = os.getenv('password')
    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/", response_class=FileResponse)
async def index(request: Request, username: str = Depends(get_current_username)):
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
        raise BaseException('error type with "path" param!')


@app.get("/list")
async def list_files(path: str | None = Query('/', alias='path'), username: str = Depends(get_current_username)):
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
async def upload_files(path: str = Form(alias='path'), files: list[UploadFile] = File(alias='files[]'),
                       username: str = Depends(get_current_username)):
    try:
        real_path = Path(path_with_root(path))
        saved_files = []
        for file in files:
            file_location = real_path.joinpath(file.filename)
            with open(file_location, "wb") as f:
                f.write(await file.read())
            saved_files.append(file.filename)
        return JSONResponse(content={"filenames": saved_files}, status_code=200)
    except BaseException as e:
        return JSONResponse(content={"detail": str(e)}, status_code=500)


@app.post("/delete")
async def delete_file(path: str = Form(alias='path'), username: str = Depends(get_current_username)):
    try:
        real_path = Path(path_with_root(path))
        if os.path.exists(real_path):
            shutil.rmtree(real_path)
        else:
            raise BaseException(f"File {path} does not exist.")
        return JSONResponse(content={}, status_code=200)
    except BaseException as e:
        return JSONResponse(content={"detail": str(e)}, status_code=500)


@app.post("/create")
async def create_folder(path: str = Form(alias='path'), username: str = Depends(get_current_username)):
    try:
        real_path = Path(path_with_root(path))
        if os.path.exists(real_path):
            raise BaseException(f"Folder {path} is existed.")
        else:
            os.makedirs(real_path, exist_ok=True)
        return JSONResponse(content={'path': path}, status_code=200)
    except BaseException as e:
        return JSONResponse(content={"detail": str(e)}, status_code=500)


@app.post("/move")
async def move_path(oldPath: str = Form(alias='oldPath'), newPath: str = Form(alias='newPath'),
                    username: str = Depends(get_current_username)):
    try:
        old_real_path = path_with_root(oldPath)
        new_real_path = path_with_root(newPath)
        if not os.path.exists(old_real_path):
            raise BaseException(f"file/Folder {oldPath} does not exist.")
        else:
            shutil.move(old_real_path, new_real_path)
        return JSONResponse(content={}, status_code=200)
    except BaseException as e:
        return JSONResponse(content={"detail": str(e)}, status_code=500)


@app.get("/openfile")
@app.get("/download")
async def download_file(background_tasks: BackgroundTasks, path: str = Query(alias='path'),
                        username: str = Depends(get_current_username)):
    try:
        real_path = Path(path_with_root(path))
        file = Path(real_path)
        if not os.path.exists(real_path):
            raise BaseException(f"File/Folder {path} does not exist.")
        if os.path.isfile(real_path):
            return FileResponse(real_path, media_type='application/octet-stream', filename=file.name)
        else:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            zip_file_path = os.path.join(temp_dir, f"{file.name}.zip")
            # 压缩目录
            shutil.make_archive(base_name=zip_file_path.replace(".zip", ""), format='zip', root_dir=real_path)
            # 定义删除临时目录的后台任务
            background_tasks.add_task(shutil.rmtree, temp_dir)
            return FileResponse(zip_file_path, media_type='application/zip', filename=f"{file.name}.zip",
                                background=background_tasks)
    except BaseException as e:
        return JSONResponse(content={"detail": str(e)}, status_code=500)


if __name__ == "__main__":
    import os

    os.environ["http_proxy"] = ""
    os.environ["https_proxy"] = ""
    logging.info('启动网狗盘: http://127.0.0.1:8007')
    logging.info('API文档: http://127.0.0.1:8007/docs')
    uvicorn.run(app, host="0.0.0.0", port=8007, timeout_keep_alive=60, reload=False)
