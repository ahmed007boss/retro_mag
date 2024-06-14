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
from glob import glob
from mysql.connector import Error
from datetime import datetime

app = Flask(__name__)
CORS(app)

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
# config = {
#     'host': '127.0.0.1',
#     'user': 'root',
#     'password': '',
#     'database': 'retro_mag'
# }

def insert_event(connection,ID, name, date, location, description, image_path, author):
    cursor = connection.cursor()
    insert_query = """
    INSERT INTO events (ID,NAME, DATE, LOCATION, DESCRIPTION, IMAGE_PATH, AUTHOR)
    VALUES (%s,%s, %s, %s, %s, %s, %s)
    """
    record = (ID,name, date, location, description, image_path, author)
    try:
        cursor.execute(insert_query, record)
        connection.commit()
        return "EVENT inserted successfully"
    except Error as e:
        return f"The error '{e}' occurred"
def delete_event(connection, event_id):
    cursor = connection.cursor()
    delete_query = "DELETE FROM events WHERE ID = %s"
    try:
        cursor.execute(delete_query, (event_id,))
        connection.commit()
        return "Record deleted successfully"
    except Error as e:
        return f"The error '{e}' occurred"
def fetch_all_events(connection):
    cursor = connection.cursor()
    select_query = "SELECT * FROM events"
    try:
        cursor.execute(select_query)
        records = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(records, columns=columns)
        return df
    except Error as e:
        print(f"The error '{e}' occurred")
        return None
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

@app.route("/EVENT/<path:filename>")
def EVENT(filename):
    return send_from_directory("EVENT", filename)

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
        data = df[["ID", "Headline", "category_ID","author"]]
        data.rename(columns={'author': 'AuthorName'}, inplace=True)

        data["Image"] = ""

        for i in range(len(df)):
            dt = df["Image_ID"].iloc[i]
            query1 = f"SELECT * FROM `image` WHERE `ID`={dt}"
            cursor.execute(query1)
            result1 = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            df1 = pd.DataFrame(result1, columns=columns)
            data["Image"].iloc[i] = "https://retromagapi.azurewebsites.net/images" + df1["image_url"].iloc[0]

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
        return "https://retromagapi.azurewebsites.net/images" + result[0]
    return None

@app.route("/GetALLMagazine", methods=["GET"])
def get_all_magazine():
    try:
        conn = mysql.connector.connect(**config)

        with conn.cursor() as cursor:
            # Fetch all necessary data in one query
            query = """
            SELECT m.ID AS magazine_ID, m.author, m.Headline, m.Image_ID, m.category_ID,
            c.ID AS category_ID, c.Name AS category_name
            FROM magazine m
            INNER JOIN category c ON m.category_ID = c.ID;
            """
            df = fetch_data(cursor, query)

            # Fetch image URLs for all magazines at once
            image_ids = df['Image_ID'].tolist()
            image_query = f"SELECT ID, image_url FROM image WHERE ID IN ({','.join(map(str, image_ids))});"
            image_df = fetch_data(cursor, image_query)
            image_mapping = dict(zip(image_df['ID'], image_df['image_url']))
            
            result = {}
            for _, row in df.iterrows():
                category_name = row['category_name']
                # print("dddd")
                # print(row['category_ID'][0])
                magazine_info = {
                    "ID": row['magazine_ID'],
                    "AuthorName": row['author'],
                    "Headline": row['Headline'],
                    "Image": f"https://retromagapi.azurewebsites.net/images{image_mapping[row['Image_ID']]}",
                    "CategoryId": row['category_ID'][0]
                }
                if category_name in result:
                    result[category_name].append(magazine_info)
                else:
                    result[category_name] = [magazine_info]

            # Fetch latest five magazines
            latest_query = "SELECT MAG_ID FROM latestFiveMagazines;"
            latest_df = fetch_data(cursor, latest_query)
            latest_magazine_ids = latest_df['MAG_ID'].tolist()
            # print(latest_magazine_ids)
            listofdata = []
            for i in range(len(latest_magazine_ids)):
                query0 = f"SELECT * FROM `magazine` WHERE `ID`={latest_magazine_ids[i]};"
                cursor.execute(query0)
                result0 = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                df0 = pd.DataFrame(result0, columns=columns)
                magazine_data = {
                    "ID": int(df0.loc[0]["ID"]),
                    "AuthorName": df0.loc[0]["author"],
                    "Headline": df0.loc[0]["Headline"],
                    "Image": f"https://retromagapi.azurewebsites.net/images{image_mapping[df0.loc[0]['Image_ID']]}",
                    "CategoryId": int(df0.loc[0]['category_ID'])
                }
                listofdata.append(magazine_data)


            # latest_query = f"""
            # SELECT m.ID AS magazine_ID, m.author, m.Headline, m.Image_ID, m.category_ID
            # FROM magazine m
            # WHERE m.ID IN ({','.join(map(str, latest_magazine_ids))});
            # """
            # latest_df = fetch_data(cursor, latest_query)

            # for _, row in latest_df.iterrows():
            #     # print(row["magazine_ID"])
            #     magazine_data = {
            #         "ID": int(row["magazine_ID"]),
            #         "AuthorName": row["author"],
            #         "Headline": row["Headline"],
            #         "Image": f"https://retromagapi.azurewebsites.net/images{image_mapping[row['Image_ID']]}",
            #         "CategoryId": int(row['category_ID'])
            #     }
                # listofdata.append(magazine_data)

            result["LatestFiveMagazines"] = listofdata
            EVENTDATA=fetch_all_events(conn)
            EVENTDATA.rename(columns={'AUTHOR': 'AuthorName'}, inplace=True)
            EVENTDATA.rename(columns={'NAME': 'HeadLine'}, inplace=True)
            EVENTDATA.rename(columns={'DATE':'EventDate'}, inplace=True)
            EVENTDATA.rename(columns={'LOCATION':'Location'}, inplace=True)
            EVENTDATA.rename(columns={'DESCRIPTION':'Paragraph'}, inplace=True)
            EVENTDATA.rename(columns={'IMAGE_PATH':'Image'}, inplace=True)
            EVENTDATA.rename(columns={'ID':'EventId'}, inplace=True)
            EVENTDATA['Image']="https://retromagapi.azurewebsites.net/EVENT"+EVENTDATA['Image']
            results_json = EVENTDATA.to_json(orient='records')         
        
        # Create a dictionary with the desired structure    
            result["Events"]=json.loads(results_json)

            processed_data = {"Model": result}
            # print(processed_data)
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

        images = [{"ID": dt["ID"], "ContextID": dt["context_id"], "ImageUrl": "https://retromagapi.azurewebsites.net/images" + dt["image_url"]} for _, dt in df2.iterrows()]
        index["Images"] = images

        videos = [{"VideoUrl": dt["video_url"]} for _, dt in df3.iterrows()]
        index["Videos"] = videos
        index["Headline"] = df0.loc[0].Headline
        index["AuthorName"] = df0.loc[0].author
        select_query = "SELECT * FROM events"
        cursor.execute(select_query)
        records = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(records, columns=columns)
        df.rename(columns={'AUTHOR': 'AuthorName'}, inplace=True)
        df.rename(columns={'NAME': 'HeadLine'}, inplace=True)
        df.rename(columns={'DATE':'EventDate'}, inplace=True)
        df.rename(columns={'LOCATION':'Location'}, inplace=True)
        df.rename(columns={'DESCRIPTION':'Paragraph'}, inplace=True)
        df.rename(columns={'IMAGE_PATH':'Image'}, inplace=True)
        df.rename(columns={'ID':'EventId'}, inplace=True)
        df['Image']="https://retromagapi.azurewebsites.net/EVENT"+df['Image']
        results_json = df.to_json(orient='records')
        index["Events"]=json.loads(results_json)

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
#                 "ImageUrl": f"https://retromagapi.azurewebsites.net/images{df2.loc[0]['image_url']}"
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

    try:
        # Get the last magazine ID
        cursor.execute("SELECT ID FROM magazine ORDER BY ID DESC LIMIT 1")
        last_id = cursor.fetchone()
        ID = 1 if not last_id else last_id[0] + 1
        new_folder_path = f"./IMAGE/{ID}"
        os.mkdir(new_folder_path)

        tab_data = request.form
        datafiles = request.files
        # print(datafiles)
        # print(tab_data)

        CategoryId = int(tab_data["CategoryId"])
        IsIncludeVideo = int(tab_data["IsIncludeVideo"])

        coverphoto = datafiles['Coverphoto']
        coverphoto_path = save_file(coverphoto, new_folder_path)

        MagazineHeadLine = tab_data["FirstMagazineHeadLine"] if IsIncludeVideo == 0 else tab_data["SecMagazineHeadLine"]
        author = tab_data["AuthorName"]
        cursor.execute("SELECT ID FROM image ORDER BY ID DESC LIMIT 1")
        last_image_id = cursor.fetchone()
        IMAGE_ID = 1 if not last_image_id else last_image_id[0] + 1

        # Insert into magazine table
        query = """
        INSERT INTO magazine (ID, Headline, category_ID, Image_ID,author)
        VALUES (%s, %s, %s, %s,%s)
        """
        cursor.execute(query, (ID, MagazineHeadLine, CategoryId, IMAGE_ID,author))
        conn.commit()

        # Insert cover photo into image table
        query = """
        INSERT INTO image (ID, MAG_ID, context_id, image_url)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (IMAGE_ID, ID, -1, coverphoto_path.replace('./IMAGE', '').replace('\\', '/')))
        conn.commit()

        cursor.execute("SELECT ID FROM context ORDER BY ID DESC LIMIT 1")
        last_context_id = cursor.fetchone()
        context_ID = 1 if not last_context_id else last_context_id[0] + 1

        if IsIncludeVideo == 1:
            cursor.execute("SELECT ID FROM videos ORDER BY ID DESC LIMIT 1")
            last_videos_id = cursor.fetchone()
            videos_ID = 1 if not last_videos_id else last_videos_id[0] + 1
            UrlVideo = tab_data["UrlVideo"]
            VideoParagraph = tab_data["VideoParagraph"]
            query = """
            INSERT INTO context (ID, MAG_ID, Context)
            VALUES (%s, %s, %s)
            """
            cursor.execute(query, (context_ID, ID, VideoParagraph))
            conn.commit()

            query = """
            INSERT INTO videos (ID, MAG_ID, video_url)
            VALUES (%s, %s, %s)
            """
            cursor.execute(query, (videos_ID, ID, UrlVideo))
            conn.commit()

            return jsonify({"ResultMessege": "Magazine added successfully"})
        else:
            # print("hi")
            entries_list = [item.split(".")[0] for item in tab_data if 'Entries' in item]
            files_list = [item.split(".")[0] for item in datafiles if 'Entries' in item]

            imagepath = []
            imageParagraph = []

            for entry in entries_list:
                if entry in files_list:
                    photo = datafiles[f"{entry}.photo"]
                    imagepath.append(save_file(photo, new_folder_path))
                else:
                    imagepath.append("")
                imageParagraph.append(tab_data[f"{entry}.Paragraph"])
            Paragraph_ID = []

            for paragraph in imageParagraph:
                if paragraph != "" and paragraph != None:
                    query = """
                    INSERT INTO context (ID, MAG_ID, Context)
                    VALUES (%s, %s, %s)
                    """
                    cursor.execute(query, (context_ID, ID, paragraph))
                    Paragraph_ID.append(context_ID)
                    context_ID += 1
                else:
                    Paragraph_ID.append(0)
            conn.commit()

            for i in range(len(imagepath)):
                if imagepath[i]:
                    IMAGE_ID += 1
                    context_id = Paragraph_ID[i] if Paragraph_ID[i] != 0 else next((num for num in Paragraph_ID[i:] if num != 0), 0)
                    query = """
                    INSERT INTO image (ID, MAG_ID, context_id, image_url)
                    VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(query, (IMAGE_ID, ID, context_id, imagepath[i].replace('./IMAGE', '').replace('\\', '/')))
            conn.commit()

            return jsonify({"ResultMessege": "Magazine added successfully"})
    
    except FileExistsError:
        return jsonify({"ResultMessege": "Error in adding magazine", "error": f"Folder '{new_folder_path}' already exists."})
    
    except Exception as e:
        print(e)
        return jsonify({"ResultMessege": "Error in adding magazine", "error": str(e)})
    
    finally:
        cursor.close()
        conn.close()

@app.route("/GetAllMagazinesWithCategories", methods=["GET"])
def GetAllMagazinesWithCategories():
    try:
        conn = mysql.connector.connect(**config)

        with conn.cursor() as cursor:
            magazine_query = "SELECT * FROM `magazine`;"
            magazine_df = fetch_data(cursor, magazine_query)

        
            listofdata = []
            for _, row in magazine_df.iterrows():
                magazine_info = {
                    "MagazineId": row['ID'],
                    "CategoryId": row['category_ID'],
                    "Headline": row['Headline'],
                    "AuthorName": row['author']
                }
                listofdata.append(magazine_info)
            query = "SELECT * FROM latestFiveMagazines;"
            cursor.execute(query)
            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(result, columns=columns)
            listofmag = []
            for i in range(len(df)):
                dt = df.loc[i]
                query3 = f"SELECT ID,category_ID,Headline,author FROM magazine WHERE ID={dt.MAG_ID};"
                cursor.execute(query3)
                result3 = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                df3 = pd.DataFrame(result3, columns=columns)
                df3["LatestId"]=dt["ID"]
                df3 .rename(columns={'ID': 'MagazineId'}, inplace=True)
                df3 .rename(columns={'category_ID': 'CategoryId'}, inplace=True)
                df3 .rename(columns={'author': 'AuthorName'}, inplace=True)
                results_jsondata = df3.to_json(orient='records')         
                listofmag.append(json.loads(results_jsondata)[0])
            ALLDATA={"AllMagazines":listofdata,"LatestFiveMag":listofmag}
            processed_data = {"Model": ALLDATA}
            return jsonify(processed_data)
    except Exception as e:
        return jsonify({"error": str(e)})     

@app.route("/DeleteMagazine", methods=["POST"])
def DeleteMagazines():
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        data = request.json
        ID = data["magazineId"]
        path = f"./IMAGE/{ID}"
        check_query = "SELECT COUNT(*) FROM latestFiveMagazines WHERE MAG_ID = %s"
        cursor.execute(check_query, (ID,))
        result = cursor.fetchone()

        exists = result[0] > 0
        if exists:
             return jsonify({"ResultMessege": "Can't Delete this magazine change it from LatestFiveMagazine First"})   
        else:
         try:
            shutil.rmtree(path)
            cursor.execute("DELETE FROM magazine WHERE ID ={}".format(ID))
            conn.commit()
            cursor.execute("DELETE FROM context WHERE MAG_ID ={}".format(ID))
            conn.commit()
            cursor.execute("DELETE FROM image WHERE MAG_ID ={}".format(ID))
            conn.commit()
            cursor.execute("DELETE FROM videos WHERE MAG_ID ={}".format(ID))
            conn.commit()
            return jsonify({"ResultMessege": "Magazine Deleted successfully"})
         except OSError as e:
            cursor.execute("DELETE FROM magazine WHERE ID ={}".format(ID))
            conn.commit()
            cursor.execute("DELETE FROM context WHERE MAG_ID ={}".format(ID))
            conn.commit()
            cursor.execute("DELETE FROM image WHERE MAG_ID ={}".format(ID))
            conn.commit()
            cursor.execute("DELETE FROM videos WHERE MAG_ID ={}".format(ID))
            conn.commit()
            return jsonify({"ResultMessege": "Magazine Deleted successfully"})
           
    except Exception as e:
        return jsonify({"error": str(e)})     

@app.route("/showfolder", methods=["GET"])
def showfolder():
    image=glob("./IMAGE/*/*")
    return {"data":image}

@app.route("/ShowEditMagazine", methods=["POST"])
def ShowEditMagazine():

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
        index["AuthorName"] = df0.loc[0].author
        index["ID"] = int(df0.loc[0].ID)
        query = f"SELECT * FROM `context` WHERE `MAG_ID`={MAG_ID};"
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(result, columns=columns)

        query2 = f"SELECT * FROM `image` WHERE `MAG_ID` = {MAG_ID}"
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

        images = [{"ID": dt["ID"], "ContextID": dt["context_id"],"ImageUrl": "https://retromagapi.azurewebsites.net/images" + dt["image_url"]} for _, dt in df2.iterrows()]
        index["Images"] = images

        videos = [{"VideoUrl": dt["video_url"]} for _, dt in df3.iterrows()]
        index["Videos"] = videos
        index["Headline"] = df0.loc[0].Headline
        index["CategoryID"] = int(df0.loc[0].category_ID)

        IsIncludeVideo=0
        if len(videos)!=0:
            IsIncludeVideo=1
        index["IsIncludeVideo"]=IsIncludeVideo

        processed_data = {"Model": index}
        return jsonify(processed_data)
    except Exception as e:
        return jsonify({"error": str(e)})
@app.route("/EditOnMagazine", methods=["POST"])
def EditOnMagazine():
    try:
        datafiles = request.files
        tab_data = request.form

        coverphoto = datafiles['Coverphoto']
        ID = int(tab_data["MagazineId"])
        path = f"./IMAGE/{ID}"
        CategoryId = int(tab_data["CategoryId"])
        IsIncludeVideo = int(tab_data["IsIncludeVideo"])
        AuthorName = tab_data["AuthorName"]

        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        try:
            shutil.rmtree(path)
        except OSError:
            pass

        cursor.execute("DELETE FROM magazine WHERE ID = %s", (ID,))
        cursor.execute("DELETE FROM context WHERE MAG_ID = %s", (ID,))
        cursor.execute("DELETE FROM image WHERE MAG_ID = %s", (ID,))
        cursor.execute("DELETE FROM videos WHERE MAG_ID = %s", (ID,))
        conn.commit()

        cursor.execute("SELECT ID FROM magazine ORDER BY ID DESC LIMIT 1")
        last_id = cursor.fetchone()
        new_ID = ID
        new_folder_path = f"./IMAGE/{new_ID}"
        os.mkdir(new_folder_path)

        coverphoto_path = save_file(coverphoto, new_folder_path)
        MagazineHeadLine = tab_data["FirstMagazineHeadLine"] if IsIncludeVideo == 0 else tab_data["SecMagazineHeadLine"]

        cursor.execute("SELECT ID FROM image ORDER BY ID DESC LIMIT 1")
        last_image_id = cursor.fetchone()
        IMAGE_ID = 1 if not last_image_id else last_image_id[0] + 1

        query = """
            INSERT INTO magazine (ID, Headline, category_ID, Image_ID, author)
            VALUES (%s, %s, %s, %s, %s)
            """
        cursor.execute(query, (new_ID, MagazineHeadLine, CategoryId, IMAGE_ID, AuthorName))
        conn.commit()

        query = """
            INSERT INTO image (ID, MAG_ID, context_id, image_url)
            VALUES (%s, %s, %s, %s)
            """
        cursor.execute(query, (IMAGE_ID, new_ID, -1, coverphoto_path.replace('./IMAGE', '').replace('\\', '/')))
        conn.commit()

        cursor.execute("SELECT ID FROM context ORDER BY ID DESC LIMIT 1")
        last_context_id = cursor.fetchone()
        context_ID = 1 if not last_context_id else last_context_id[0] + 1

        if IsIncludeVideo == 1:
            cursor.execute("SELECT ID FROM videos ORDER BY ID DESC LIMIT 1")
            last_videos_id = cursor.fetchone()
            videos_ID = 1 if not last_videos_id else last_videos_id[0] + 1
            UrlVideo = tab_data["UrlVideo"]
            VideoParagraph = tab_data["VideoParagraph"]

            query = """
                INSERT INTO context (ID, MAG_ID, Context)
                VALUES (%s, %s, %s)
                """
            cursor.execute(query, (context_ID, new_ID, VideoParagraph))
            conn.commit()

            query = """
                INSERT INTO videos (ID, MAG_ID, video_url)
                VALUES (%s, %s, %s)
                """
            cursor.execute(query, (videos_ID, new_ID, UrlVideo))
            conn.commit()

            return jsonify({"ResultMessege": "Magazine Updated successfully"})

        else:
            entries_list = [item.split(".")[0] for item in tab_data if 'Entries' in item]
            files_list = [item.split(".")[0] for item in datafiles if 'Entries' in item]
            entries_list = list(set(entries_list))

            imagepath = []
            imageParagraph = []

            for entry in range(len(entries_list)):
                if "Entries[{}]".format(entry) in files_list:
                    photo = datafiles["Entries[{}].photo".format(entry)]
                    imagepath.append(save_file(photo, new_folder_path))
                else:
                    imagepath.append("")
                imageParagraph.append(tab_data["Entries[{}].Paragraph".format(entry)])

            Paragraph_ID = []

            for paragraph in imageParagraph:
                if paragraph:
                    query = """
                        INSERT INTO context (ID, MAG_ID, Context)
                        VALUES (%s, %s, %s)
                        """
                    cursor.execute(query, (context_ID, new_ID, paragraph))
                    Paragraph_ID.append(context_ID)
                    context_ID += 1
                else:
                    Paragraph_ID.append(0)
            conn.commit()

            for i in range(len(imagepath)):
                if imagepath[i]:
                    IMAGE_ID += 1
                    context_id = Paragraph_ID[i] if Paragraph_ID[i] != 0 else next((num for num in Paragraph_ID[i:] if num != 0), 0)
                    query = """
                        INSERT INTO image (ID, MAG_ID, context_id, image_url)
                        VALUES (%s, %s, %s, %s)
                        """
                    cursor.execute(query, (IMAGE_ID, new_ID, context_id, imagepath[i].replace('./IMAGE', '').replace('\\', '/')))
            conn.commit()

            return jsonify({"ResultMessege": "Magazine updated successfully"})

    except FileExistsError:
        return jsonify({"ResultMessege": "Error in updated magazine", "error": f"Folder '{new_folder_path}' already exists."})

    except Exception as e:
        print(e)
        return jsonify({"ResultMessege": "Error in updated magazine", "error": str(e)})
@app.route("/ShowHeadIdMagazine", methods=["GET"])
def ShowHeadIdMagazine():

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        query = f"SELECT ID,Headline FROM `magazine`"
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(result, columns=columns)
        results_json = df.to_json(orient='records')         
        
        # Create a dictionary with the desired structure    
        response_data = {"Model": json.loads(results_json)}
        return response_data

    
    except Exception as e:
        print(e)
        return jsonify({"ResultMessege": "Error in show data", "error": str(e)})
    
@app.route("/ShowLatestEditMagazine", methods=["GET"])
def ShowLatestEditMagazine():

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        query = f"SELECT ID,Headline FROM `magazine`"
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df0 = pd.DataFrame(result, columns=columns)
        results_json = df0.to_json(orient='records')         
        query = "SELECT * FROM latestFiveMagazines;"
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(result, columns=columns)
        listofdata = []
        for i in range(len(df)):
            dt = df.loc[i]
            query3 = f"SELECT * FROM magazine WHERE ID={dt.MAG_ID};"
            cursor.execute(query3)
            result3 = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            df3 = pd.DataFrame(result3, columns=columns)
            df3["LatestId"]=dt["ID"]
            df3.rename(columns={'ID': 'MagId'}, inplace=True)
            results_jsondata = df3.to_json(orient='records')         
            listofdata.append(json.loads(results_jsondata))
        data={"AllMag":json.loads(results_json),"LatestFiveMagazine":listofdata}  
        response_data = {"Model": data}
        return response_data
    
    except Exception as e:
        print(e)
        return jsonify({"ResultMessege": "Error in show data", "error": str(e)})

@app.route("/EditLatestFiveMagazine", methods=["POST"])
def EditLatestFiveMagazine():
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        data = request.json
        print(data)
        LatestId = int(data["latestId"])
        MagazineId = int(data["magazineId"])
        NewMagazineId = int(data["newMagazineId"])

        update_query = """
            UPDATE latestFiveMagazines 
            SET MAG_ID = %s 
            WHERE ID = %s AND MAG_ID = %s
        """
        
        cursor.execute(update_query, (NewMagazineId, LatestId, MagazineId))
        conn.commit()

        return jsonify({"ResultMessege": "Replaced successfully"})
    
    except Error as e:
        print(e)
        return jsonify({"ResultMessege": "Error in updated", "error": str(e)})
@app.route("/AddEvent", methods=["POST"])
def AddEvent():
    try:
        tab_data = request.form
        datafiles = request.files
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT ID FROM events ORDER BY ID DESC LIMIT 1")
        last_id = cursor.fetchone()
        ID = 1 if not last_id else last_id[0] + 1
        new_folder_path = f"./EVENT/{ID}"
        os.mkdir(new_folder_path)
        # print(tab_data)
        author = tab_data["AuthorName"]
        Headline = tab_data["HeadLine"]
        EventDate = tab_data['EventDate']
        Location = tab_data['Location']
        Paragraph = tab_data['Paragraph']
        coverphoto = datafiles['Coverphoto']
        coverphoto_path = save_file(coverphoto, new_folder_path)
        coverphoto_path=coverphoto_path.replace('./EVENT', '').replace('\\', '/')
        date_object = datetime.strptime(EventDate, '%m/%d/%Y %I:%M:%S %p')


# Get the day of the week (Monday = 0, Sunday = 6)
        day_of_week = date_object.weekday()

# Convert day_of_week to the actual name of the day
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_name = days_of_week[day_of_week]
        formatted_date_string = date_object.strftime('%Y-%m-%d') + f', ({day_name})'

        MESSAGE=insert_event(conn,ID, Headline, formatted_date_string, Location, Paragraph, coverphoto_path, author)
        return jsonify({"ResultMessege":MESSAGE})
    except Exception as e:
        print(e)
        return jsonify({"ResultMessege": "Error in insert EVENT", "error": str(e)})
@app.route("/GetDataEvent", methods=["POST"])
def GetDataEvent():
    try:
        conn = mysql.connector.connect(**config)

        cursor = conn.cursor()
        data = request.json
        EventId = int(data["eventId"])
        select_query = "SELECT * FROM events WHERE ID={}".format(EventId)
        cursor.execute(select_query)
        records = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(records, columns=columns)
        df.rename(columns={'AUTHOR': 'AuthorName'}, inplace=True)
        df.rename(columns={'NAME': 'HeadLine'}, inplace=True)
        df.rename(columns={'DATE':'EventDate'}, inplace=True)
        df.rename(columns={'LOCATION':'Location'}, inplace=True)
        df.rename(columns={'DESCRIPTION':'Paragraph'}, inplace=True)
        df.rename(columns={'IMAGE_PATH':'Image'}, inplace=True)
        df.rename(columns={'ID':'EventId'}, inplace=True)
        df['Image']="https://retromagapi.azurewebsites.net/EVENT"+df['Image']
        results_json = df.to_json(orient='records')         
        
        # Create a dictionary with the desired structure    
        return {"ModelList":json.loads(results_json)}
    except Exception as e:
        print(e)
        return jsonify({"ResultMessege": "Error in updated", "error": str(e)})
@app.route("/GetAllDataEvent", methods=["GET"])
def GetAllDataEvent():
    try:
        conn = mysql.connector.connect(**config)

        cursor = conn.cursor()
        # data = request.json
        # EventId = int(data["eventId"])
        select_query = "SELECT * FROM events"
        cursor.execute(select_query)
        records = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(records, columns=columns)
        df.rename(columns={'AUTHOR': 'AuthorName'}, inplace=True)
        df.rename(columns={'NAME': 'HeadLine'}, inplace=True)
        df.rename(columns={'DATE':'EventDate'}, inplace=True)
        df.rename(columns={'LOCATION':'Location'}, inplace=True)
        df.rename(columns={'DESCRIPTION':'Paragraph'}, inplace=True)
        df.rename(columns={'IMAGE_PATH':'Image'}, inplace=True)
        df.rename(columns={'ID':'EventId'}, inplace=True)
        df['Image']="https://retromagapi.azurewebsites.net/EVENT"+df['Image']
        results_json = df.to_json(orient='records')         
        
        # Create a dictionary with the desired structure    
        return {"ModelList":json.loads(results_json)}
    except Exception as e:
        print(e)
        return jsonify({"ResultMessege": "Error in updated", "error": str(e)})
@app.route("/GetDataEventDelete", methods=["GET"])
def GetDataEventDelete():
    try:
        conn = mysql.connector.connect(**config)

        cursor = conn.cursor()
        select_query = "SELECT ID,NAME,AUTHOR,DATE,LOCATION FROM events"
        cursor.execute(select_query)
        records = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(records, columns=columns)
        df.rename(columns={'AUTHOR': 'AuthorName'}, inplace=True)
        df.rename(columns={'NAME': 'HeadLine'}, inplace=True)
        df.rename(columns={'ID':'EventId'}, inplace=True)
        df.rename(columns={'DATE':'EventDate'}, inplace=True)
        df.rename(columns={'LOCATION':'Location'}, inplace=True)
        results_json = df.to_json(orient='records')         
        
        # Create a dictionary with the desired structure    
        return {"ModelList":json.loads(results_json)}
    except Exception as e:
        print(e)
        return jsonify({"ResultMessege": "Error in updated", "error": str(e)})

  
@app.route("/DeleteEvent", methods=["POST"])
def DeleteEvent():
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        data = request.json
        ID = data["eventId"]
        path = f"./EVENT/{ID}"

# Remove the directory and its contents
        try:
            shutil.rmtree(path)
            cursor.execute("DELETE FROM events WHERE ID ={}".format(ID))
            conn.commit()
            return jsonify({"ResultMessege": "EVENT Deleted successfully"})
        except OSError as e:
            cursor.execute("DELETE FROM events WHERE ID ={}".format(ID))
            conn.commit()
            
            return jsonify({"ResultMessege": "Magazine Deleted successfully"})
                # return jsonify({"error": str(e)})     

    except Exception as e:
        return jsonify({"error": str(e)})
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
