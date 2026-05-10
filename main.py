from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# import routes
from routes.upload import router as upload_router
from routes.similarity import router as similarity_router  
from routes.spelling import router as spelling_router
from routes.grammar import router as grammar_router 
from routes.grading import router as grading_router

app = FastAPI()

# allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Backend Running...."}

# include routes
app.include_router(upload_router)
app.include_router(similarity_router)  
app.include_router(spelling_router)
app.include_router(grammar_router)
app.include_router(grading_router)