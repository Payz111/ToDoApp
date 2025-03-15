from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette import status
from ..models import Todos
from ..database import SessionLocal
from .auth import get_current_user
from starlette.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

tepmlates = Jinja2Templates(directory="TodoApp/templates")

router = APIRouter(
    prefix='/todos',
    tags=['todos']
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class TodoRequest(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(min_length=3, max_length=100)
    priority: int = Field(gt=0, lt=6)
    complete: bool


def redirect_to_login():
    redirect_response = RedirectResponse(url='/auth/login-page', status_code=status.HTTP_302_FOUND)
    redirect_response.delete_cookie(key='access_token')
    return redirect_response

### Pages ###
@router.get('/todo-page')
async def render_todo_page(request: Request, db: db_dependency):
    try:
        user = await get_current_user(request.cookies.get('access_token'))
        if user is None:
            return redirect_to_login()

        todos = db.query(Todos).filter(Todos.owner_id == user.get('id')).all()
        print(f"ID задач для пользователя {user.get('id')}: {[t.id for t in todos]}")

        return tepmlates.TemplateResponse('todo.html', {'request': request, 'todos': todos, 'user': user})
    except:
        return redirect_to_login()


@router.get('/add-todo-page')
async def render_todo_page(request: Request):
    try:
        user = await get_current_user(request.cookies.get('access_token'))

        if user is None:
            return redirect_to_login()

        return tepmlates.TemplateResponse("add-todo.html", {'request': request, "user": user})

    except:
        return redirect_to_login()


@router.get("/edit-todo-page/{todo_id}")
async def render_edit_todo_page(request: Request, todo_id: int, db: db_dependency):
    try:
        user = await get_current_user(request.cookies.get('access_token'))
        print(f"Проверка пользователя: {user}")

        if user is None:
            return redirect_to_login()

        print(f"Попытка получить задачу {todo_id} для пользователя {user.get('id')}")

        # Теперь проверяем не только ID задачи, но и владельца
        todo = db.query(Todos).filter(Todos.id == todo_id, Todos.owner_id == user.get('id')).first()

        # Выводим все задачи в БД
        todos_in_db = db.query(Todos).all()
        print("Все задачи в БД:", [(t.id, t.owner_id) for t in todos_in_db])

        if todo is None:
            print(f"Задача с ID {todo_id} не найдена для пользователя {user.get('id')}!")
            return redirect_to_login()

        print(f"Найденная задача: {todo.id} (принадлежит {todo.owner_id})")

        return tepmlates.TemplateResponse("edit-todo.html", {"request": request, "todo": todo, "user": user})

    except Exception as e:
        print(f"Ошибка: {e}")
        return redirect_to_login()




'''
@router.get("/edit-todo-page/{todo_id}")
async def render_edit_todo_page(request: Request, todo_id: int, db: db_dependency):
    print(todo_id)
    try:
        user = await get_current_user(request.cookies.get('access_token'))
        print(user is None)
        if user is None:
            return redirect_to_login()
        print(1)
        #todo = db.query(Todos).filter(Todos.id == todo_id).first()
        todo = db.query(Todos).filter(Todos.id == todo_id, Todos.owner_id == user.get('id')).first()
        print([t.id for t in db.query(Todos).all()])

        print(todo.id)
        return tepmlates.TemplateResponse("edit-todo.html", {"request": request, "todo": todo, "user": user})
        print(2)
    except:
        return redirect_to_login()

'''

### Endpoints ###
@router.get('/', status_code=status.HTTP_200_OK)
async def read_all(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    return db.query(Todos).filter(Todos.owner_id == user.get('id')).all()


@router.get("/todo/{todo_id}", status_code=status.HTTP_200_OK)
async def read_todo(user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    todo_model = db.query(Todos).filter(Todos.id == todo_id)\
        .filter(Todos.owner_id == user.get('id')).first()
    if todo_model is not None:
        return todo_model
    raise HTTPException(status_code=404, detail='Todo not found.')


@router.post('/todo', status_code=status.HTTP_201_CREATED)
async def create_todo(user: user_dependency, db: db_dependency,
                      todo_request: TodoRequest):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    todo_model = Todos(**todo_request.dict(), owner_id=user.get('id'))

    db.add(todo_model)
    db.commit()


@router.put('/todo/{todo_id}', status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(user: user_dependency, db: db_dependency,
                      todo_request: TodoRequest,
                      todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')

    todo_model = db.query(Todos).filter(Todos.id == todo_id)\
        .filter(Todos.owner_id == user.get('id')).first()
    if todo_model is None:
        raise HTTPException(status_code=404, detail='Todo not found.')

    todo_model.title = todo_request.title
    todo_model.description = todo_request.description
    todo_model.priority = todo_request.priority
    todo_model.complete = todo_request.complete

    db.add(todo_model)
    db.commit()


@router.delete('/todo/{todo_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')

    todo_model = db.query(Todos).filter(Todos.id == todo_id)\
        .filter(Todos.owner_id == user.get('id')).first()
    if todo_model is None:
        raise HTTPException(status_code=404, detail='Todo not found.')

    db.query(Todos).filter(Todos.id == todo_id)\
        .filter(Todos.owner_id == user.get('id')).delete()

    db.commit()
