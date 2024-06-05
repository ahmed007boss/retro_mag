from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
import pandas as pd
import mysql.connector
import os
from werkzeug.utils import secure_filename
from glob import glob
import json
import shutil
import urllib.parse


app = Flask(__name__)
CORS(app)

# Define the connection parameters
# config = {
#     'user': 'avnadmin',
#     'password': 'AVNS_9E9kqttyyPwEk-U3Hpg',
#     'host': 'mysql-6ae2b8d-ahmed-f254.l.aivencloud.com',
#     'database': 'defaultdb',
#     'port': 23655,
#     'charset': 'utf8mb4',
#     'connect_timeout': 10,
#     'ssl_ca': 'ca-cert.pem',  # Path to the SSL CA certificate
#     'ssl_verify_cert': True  # Verify the server certificate
# }
config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'retro_mag'
}
@app.route("/")
def root():
    return render_template_string("""
    <h2 style="text-align:center">
        Click
        <a href="/docs">API DOC</a>
        to see the API doc
    </h2>
    """)

@app.route("/images/<path:filename>")
def images(filename):
    return send_from_directory("IMAGE", filename)

@app.route("/get_category", methods=["GET"])
def get_category():
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        query = "SELECT * FROM `category`"
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(result, columns=columns)
        processed_data = {"result": df.to_dict(orient='records')}
        return jsonify(processed_data)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/GetCategoryMagazine", methods=["POST"])
def get_category_magazine():
    try:
        conn = mysql.connector.connect(**config)

        cursor = conn.cursor()
        data = request.json
        category_ID = data["categoryId"]
        query = f"SELECT * FROM `magazine` WHERE `category_ID`={category_ID};"
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(result, columns=columns)
        data = df[["ID", "Headline", "category_ID"]]
        data["Image"] = ""

        for i in range(len(df)):
            dt = df["Image_ID"].iloc[i]
            query1 = f"SELECT * FROM `image` WHERE `ID`={dt}"
            cursor.execute(query1)
            result1 = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            df1 = pd.DataFrame(result1, columns=columns)
            data["Image"].iloc[i] = "http://10.5.50.193:8080/images" + df1["image_url"].iloc[0]

        processed_data = {"Magazines": data.to_dict(orient='records')}
        return jsonify(processed_data)
    except Exception as e:
        return jsonify({"error": str(e)})

def fetch_data(cursor, query):
    conn = mysql.connector.connect(**config)

    cursor = conn.cursor()
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    result = cursor.fetchall()
    df = pd.DataFrame(result, columns=columns)
    return df

def fetch_image_url(cursor, image_id):
    conn = mysql.connector.connect(**config)

    cursor = conn.cursor()
    query = f"SELECT image_url FROM `image` WHERE `ID`={image_id}"
    cursor.execute(query)
    result = cursor.fetchone()
    if result:
        return "http://10.5.50.193:8080/images" + result[0]
    return None

@app.route("/GetALLMagazine", methods=["GET"])
def get_all_magazine():
    try:
        conn = mysql.connector.connect(**config)

        with conn.cursor() as cursor:
            magazine_query = "SELECT * FROM `magazine`;"
            magazine_df = fetch_data(cursor, magazine_query)

            category_query = "SELECT * FROM `category`;"
            category_df = fetch_data(cursor, category_query)

            merged_df = pd.merge(magazine_df, category_df, left_on='category_ID', right_on='ID', suffixes=('_magazine', '_category'))

            result = {}
            for _, row in merged_df.iterrows():
                category_name = row['Name']
                magazine_info = {
                    "ID": row['ID_magazine'],
                    # "NAME": row['NAME'],
                    "Headline": row['Headline'],
                    "Image": fetch_image_url(cursor, row['Image_ID'])
                }
                if category_name in result:
                    result[category_name].append(magazine_info)
                else:
                    result[category_name] = [magazine_info]
            query_latest = "SELECT * FROM latestFiveMagazines;"
            latest_df = fetch_data(cursor, query_latest)
            listofdata = []
            for _, row in latest_df.iterrows():
                query3 = f"SELECT * FROM magazine WHERE ID={row['MAG_ID']};"
                five_df = fetch_data(cursor, query3)
                query2 = f"SELECT * FROM image WHERE ID={five_df.loc[0]['Image_ID']};"
                image_df = fetch_data(cursor, query2)
                merged_df2 = pd.merge(five_df, category_df, left_on='category_ID', right_on='ID', suffixes=('_magazine', '_category'))

                magazine_data = {
                "ID": int(merged_df2.loc[0]["ID_magazine"]),
                # "NAME": merged_df2.loc[0]["NAME"],
                "Headline": merged_df2.loc[0]["Headline"],
                "Image": f"http://10.5.50.193:8080/images{image_df.loc[0]['image_url']}"
                ,"CategoryId":int(merged_df2.loc[0]['category_ID'])
                }
                listofdata.append(magazine_data)
                result["LatestFiveMagazines"]=listofdata

            processed_data = {"Model": result}
            return jsonify(processed_data)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/GetDataMagazine", methods=["POST"])
def get_data_magazine():
    try:
        conn = mysql.connector.connect(**config)

        cursor = conn.cursor()

        data = request.json
        index = {}
        MAG_ID = data["magId"]

        query0 = f"SELECT * FROM `magazine` WHERE `ID`={MAG_ID};"
        cursor.execute(query0)
        result0 = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df0 = pd.DataFrame(result0, columns=columns)

        query = f"SELECT * FROM `context` WHERE `MAG_ID`={MAG_ID};"
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(result, columns=columns)

        query2 = f"SELECT * FROM `image` WHERE `MAG_ID` = {MAG_ID} AND `context_id` != -1;"
        cursor.execute(query2)
        result2 = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df2 = pd.DataFrame(result2, columns=columns)

        query3 = f"SELECT * FROM `videos` WHERE `MAG_ID`={MAG_ID};"
        cursor.execute(query3)
        result3 = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df3 = pd.DataFrame(result3, columns=columns)

        context = [{"ID": dt["ID"], "Paragraph": dt["Context"]} for _, dt in df.iterrows()]
        index["Context"] = context

        images = [{"ID": dt["ID"], "ContextID": dt["context_id"], "ImageUrl": "http://10.5.50.193:8080/images" + dt["image_url"]} for _, dt in df2.iterrows()]
        index["Images"] = images

        videos = [{"VideoUrl": "http://10.5.50.193:8080/images" + dt["video_url"]} for _, dt in df3.iterrows()]
        index["Videos"] = videos
        index["Headline"] = df0.loc[0].Headline
        # index["Name"] = df0.loc[0].NAME

        processed_data = {"Model": index}
        return jsonify(processed_data)
    except Exception as e:
        return jsonify({"error": str(e)})
# @app.route("/latestfivemagazines", methods=["GET"])
# def get_latestFiveMagazines():
#     try:
#         # Fetch the latest five magazines
#         query = "SELECT * FROM latestFiveMagazines;"
#         cursor.execute(query)
#         result = cursor.fetchall()
#         columns = [desc[0] for desc in cursor.description]
#         df = pd.DataFrame(result, columns=columns)
        
#         listofdata = []

#         for i in range(len(df)):
#             dt = df.loc[i]

#             # Fetch magazine details by ID
#             query3 = f"SELECT * FROM magazine WHERE ID={dt.MAG_ID};"
#             cursor.execute(query3)
#             result3 = cursor.fetchall()
#             columns = [desc[0] for desc in cursor.description]
#             df3 = pd.DataFrame(result3, columns=columns)

#             # Fetch image details by Image_ID from magazine details
#             query2 = f"SELECT * FROM image WHERE ID={df3.loc[0]['Image_ID']};"
#             cursor.execute(query2)
#             result2 = cursor.fetchall()
#             columns = [desc[0] for desc in cursor.description]
#             df2 = pd.DataFrame(result2, columns=columns)

#             # Construct the data dictionary for each magazine
#             magazine_data = {
#                 "ID": str(df3.loc[0]["ID"]),
#                 "NAME": df3.loc[0]["NAME"],
#                 "Headline": df3.loc[0]["Headline"],
#                 "ImageUrl": f"http://10.5.50.193:8080/images{df2.loc[0]['image_url']}"
#             }

#             listofdata.append(magazine_data)

#         data = {"Model": listofdata}
#         # print()
#         return data

#     except Exception as e:
#         return jsonify({"error": str(e)})
# class Photo(BaseModel):
#     contentType: str
#     contentDisposition: str
#     headers: Dict[str, List[str]]
#     length: int
#     name: str
#     fileName: str

# class Entry(BaseModel):
#     paragraph: str
#     photo: Optional[Photo] = None

# class RequestData(BaseModel):
#     coverphoto: Photo
#     categoryId: int
#     firstMagazineHeadLine: str
#     secMagazineHeadLine: Optional[str] = None
#     videoParagraph: Optional[str] = None
#     urlVideo: Optional[str] = None
#     isIncludeVideo: int
#     entries: List[Entry]
def save_file(file,path):
    try:
        # print(file.filename)
        if file.filename:
            filename = secure_filename(file.filename)   
            file_path = os.path.join(path, filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.stream, buffer)
            return file_path
        else:
            return ""
    except:
        return ""

@app.route("/AddMagazine", methods=["POST"])
def get_AddMagazine():
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()

    # Get the last magazine ID
    cursor.execute("SELECT ID FROM magazine ORDER BY ID DESC LIMIT 1")
    last_id = cursor.fetchone()
    ID = 1 if not last_id else last_id[0] + 1

    new_folder_path = f"./IMAGE/{ID}"
    
    try:
        os.mkdir(new_folder_path)
        
        tab_data = request.form
        datafiles = request.files

        CategoryId = int(tab_data["CategoryId"])
        IsIncludeVideo = int(tab_data["IsIncludeVideo"])

        coverphoto = datafiles['Coverphoto']
        coverphoto_path = save_file(coverphoto, new_folder_path)
        
        MagazineHeadLine = tab_data["FirstMagazineHeadLine"] if IsIncludeVideo == 0 else tab_data["SecMagazineHeadLine"]
        
        tab_data_keys = tab_data.keys()
        datafiles_list_keys = datafiles.keys()
       
        entries_list = [item.split(".")[0] for item in tab_data_keys if 'Entries' in item]
        files_list = [item.split(".")[0] for item in datafiles_list_keys if 'Entries' in item]

        imagepath = []
        imageParagraph = []

        for entry in entries_list:
            if entry in files_list:
                photo = datafiles[f"{entry}.photo"]
                imagepath.append(save_file(photo, new_folder_path))
            else:
                imagepath.append("")
            imageParagraph.append(tab_data[f"{entry}.Paragraph"])

        cursor.execute("SELECT ID FROM image ORDER BY ID DESC LIMIT 1")
        last_image_id = cursor.fetchone()
        IMAGE_ID = 1 if not last_image_id else last_image_id[0] + 1

        query = """
        INSERT INTO magazine (ID, Headline, category_ID, Image_ID)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (ID, MagazineHeadLine, CategoryId, IMAGE_ID))
        conn.commit()

        query = """
        INSERT INTO image (ID, MAG_ID, context_id, image_url)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (IMAGE_ID, ID, -1, coverphoto_path.replace('./IMAGE', '').replace('\\', '/')))
        conn.commit()

        cursor.execute("SELECT ID FROM context ORDER BY ID DESC LIMIT 1")
        last_context_id = cursor.fetchone()
        context_ID = 1 if not last_context_id else last_context_id[0] + 1

        Paragraph_ID = []

        for paragraph in imageParagraph:
            if paragraph!="":
                query = """
                INSERT INTO context (ID, MAG_ID, Context)
                VALUES (%s, %s, %s)
                """
                # print(query)
                cursor.execute(query, (context_ID, ID, paragraph))
                Paragraph_ID.append(context_ID)
                context_ID += 1
            else:
                Paragraph_ID.append(0)
        conn.commit()
        print("TRUE")

        for i in range(len(imagepath)):
            if Paragraph_ID[i] == 0 and imagepath[i]:
                first_non_zero = next((num for num in Paragraph_ID[i:] if num != 0), None)
                if first_non_zero:
                    IMAGE_ID += 1
                    query = """
                    INSERT INTO image (ID, MAG_ID, context_id, image_url)
                    VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(query, (IMAGE_ID, ID, first_non_zero, imagepath[i].replace('./IMAGE', '').replace('\\', '/')))
            elif Paragraph_ID[i] != 0 and imagepath[i]:
                IMAGE_ID += 1
                query = """
                INSERT INTO image (ID, MAG_ID, context_id, image_url)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(query, (IMAGE_ID, ID, Paragraph_ID[i], imagepath[i].replace('./IMAGE', '').replace('\\', '/')))
        conn.commit()
        return jsonify({"ResultMessege": "Magazine added successfully"})
    except FileExistsError:
        return jsonify({"ResultMessege": "Error in adding magazine", "error": f"Folder '{new_folder_path}' already exists."})
    except Exception as e:
        print("[ِسس]")
        return jsonify({"ResultMessege": "Error in adding magazine", "error": str(e)})
    finally:
        cursor.close()
        conn.close()
      
@app.route("/EditMagazine", methods=["GET"])
def get_EditMagazine():
    try:
        conn = mysql.connector.connect(**config)

        with conn.cursor() as cursor:
            magazine_query = "SELECT * FROM `magazine`;"
            magazine_df = fetch_data(cursor, magazine_query)

        
            listofdata = []
            for _, row in magazine_df.iterrows():
                magazine_info = {
                    "ID": row['ID'],
                    "CategoryID": row['category_ID'],
                    "Headline": row['Headline']
                }
                listofdata.append(magazine_info)
                

            processed_data = {"Model": listofdata}
            return jsonify(processed_data)
    except Exception as e:
        return jsonify({"error": str(e)})     





if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
