"""练习路由：GET /api/pra/{book_id}"""

from fastapi import APIRouter, Path, Query, HTTPException
from pydantic import BaseModel
router = APIRouter(tags=["pra"])


@router.get("/pra/{book_id}")
async def pra(book_id: int = Path(..., gt=0, lt=100)):
    return {"msg": f"这是第{book_id}本书"}

@router.get("/new/newList")
async def new_list(skip:int=Query(...,description='跳过的记录数',lt=100),limit:int=10):
    return {"skip":skip,"limit":limit}

class User(BaseModel):
    username: str
    email: str
    password: str
@router.post('/register')
async def register(user:User):
    return {"username":user.username,"email":user.email,"password":user.password}

@router.get('/new/{id}')
async def get_news(id:int):
    id_list=[1,2,3,4]
    if id not in id_list:
        raise HTTPException(status_code=404,detail='not exist')
    return {"id":id}


def register_middleware(app):
    @app.middleware("http")
    async def middleware(request, call_next):
        print("中间件开始处理 -- start")

        response = await call_next(request)

        print("中间件处理完成 -- end")
        return response