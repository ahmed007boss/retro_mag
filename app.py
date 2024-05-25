import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse,JSONResponse
import pandas as pd
from fastapi.staticfiles import StaticFiles
import shutil
import os
import mysql.connector

from mysql.connector import errorcode

# Define the connection parameters
config = {
    'user': 'avnadmin',
    'password': 'AVNS_9E9kqttyyPwEk-U3Hpg',
    'host': 'mysql-6ae2b8d-ahmed-f254.l.aivencloud.com',
    'database': 'defaultdb',
    'port': 23655,
    'charset': 'utf8mb4',
    'connect_timeout': 10,
    'ssl_ca': 'ca-cert.pem',  # Path to the SSL CA certificate
    'ssl_verify_cert': True  # Verify the server certificate
}
conn = mysql.connector.connect(**config)
app = FastAPI(
    description="retro mag"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/images", StaticFiles(directory="IMAGE"), name="data")
@app.get("/", response_class=HTMLResponse, tags=["Root"])
async def root():
    return """
    <h2 style="text-align:center">
        Click
        <a href="/docs">API DOC</a>
        to see the API doc
    </h2>
    """

@app.get("/get_category", tags=["Data Processing"])
async def process_data():
    try:
        cursor = conn.cursor()
        query = """SELECT * FROM `category`"""
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(result, columns=columns)
        processed_data = {"result":df.to_dict(orient='records')}
        return processed_data
    except Exception as e:
        return {"error": str(e)}
    finally:
        cursor.close()

@app.post("/get_category_magazine", tags=["Data Processing"])
async def process_data(data:dict):
    try:
        category_ID=data["category_ID"]
        cursor = conn.cursor()
        query = """SELECT * FROM `magazine` WHERE `category_ID`={};""".format(category_ID)
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(result, columns=columns)
        data=df[["ID","NAME","Headline","category_ID"]]
        data["Image"]=""
        for i in range(len(df)):
            dt=df["Image_ID"].loc[i]
            query1 = """SELECT * FROM `image` WHERE `ID`={}""".format(dt)
            cursor.execute(query1)
            result1 = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            df1 = pd.DataFrame(result1, columns=columns)
            data["Image"].loc[i]="http://192.168.1.224:8000/images"+df1["image_url"].loc[0]
        


        processed_data = {"result":data.to_dict(orient='records')}
        return processed_data
    except Exception as e:
        return {"error": str(e)}
    finally:
        cursor.close()
def fetch_data(cursor, query):
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    result = cursor.fetchall()
    df = pd.DataFrame(result, columns=columns)
    return df

def fetch_image_url(cursor, image_id):
    query = f"SELECT image_url FROM `image` WHERE `ID`={image_id}"
    cursor.execute(query)
    result = cursor.fetchone()
    if result:
        return "http://192.168.1.224:8000/images" + result[0]
    return None
@app.get("/GetALLMagazine", tags=["Data Processing"])
async def process_data():
    try:
        with conn.cursor() as cursor:
            # Fetch magazine data
            magazine_query = """SELECT * FROM `magazine`;"""
            magazine_df = fetch_data(cursor, magazine_query)

            # Fetch category data
            category_query = """SELECT * FROM `category`;"""
            category_df = fetch_data(cursor, category_query)

            # Merge magazine and category data
            merged_df = pd.merge(magazine_df, category_df, left_on='category_ID', right_on='ID', suffixes=('_magazine', '_category'))

            # Prepare result dictionary
            result = {}
            for _, row in merged_df.iterrows():
                category_name = row['Name']
                magazine_info = {
                    "ID": row['ID_magazine'],
                    "NAME": row['NAME'],
                    "Headline": row['Headline'],
                    "Image": fetch_image_url(cursor, row['Image_ID'])
                }
                if category_name in result:
                    result[category_name].append(magazine_info)
                else:
                    result[category_name] = [magazine_info]

            processed_data = {"Model": result}
            return processed_data
    except Exception as e:
        return {"error": str(e)}
    finally:
        cursor.close()

@app.post("/GetDataMagazine", tags=["Data Processing"])
async def process_data(data: dict):
    cursor = conn.cursor()
    try:
        index = {}
        # print(data)
        MAG_ID = data["magId"]

        # Retrieve context data
        query0 = """SELECT * FROM `magazine` WHERE `ID`={};""".format(MAG_ID)
        cursor.execute(query0)
        result0 = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df0 = pd.DataFrame(result0, columns=columns)

        # Retrieve context data
        query = """SELECT * FROM `context` WHERE `MAG_ID`={};""".format(MAG_ID)
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(result, columns=columns)

        # Retrieve image data
        query2 = """SELECT * FROM `image` WHERE `MAG_ID`={};""".format(MAG_ID)
        cursor.execute(query2)
        result2 = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df2 = pd.DataFrame(result2, columns=columns)

        # Retrieve video data
        query3 = """SELECT * FROM `videos` WHERE `MAG_ID`={};""".format(MAG_ID)
        cursor.execute(query3)
        result3 = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df3 = pd.DataFrame(result3, columns=columns)

        # Process context data
        context = [{"ID": dt["ID"], "Paragraph": dt["text"]} for _, dt in df.iterrows()]
        # index.append({"Context": context})
        index["Context"]=context

        # Process image data
        images = [{"ID": dt["ID"], "ContextID": dt["context_id"], "ImageUrl": "http://192.168.1.224:8000/images" + dt["image_url"]} for _, dt in df2.iterrows()]
        # index.append({"Images": images})
        index["Images"]= images

        # Process video data
        videos = [{"VideoUrl": "http://192.168.1.224:8000/images" + dt["video_url"]} for _, dt in df3.iterrows()]
        # index.append({"Videos": videos})
        index["Videos"]=videos
        index["Headline"]=df0.loc[0].Headline
        processed_data = {"Model": index}
        return processed_data
    
    except Exception as e:
        return {"error": str(e)}
    finally:
        cursor.close()
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
