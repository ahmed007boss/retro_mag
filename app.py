from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
import pandas as pd
import mysql.connector
import os

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
conn = mysql.connector.connect(**config)
cursor = conn.cursor()

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
        data = request.json
        category_ID = data["categoryId"]
        query = f"SELECT * FROM `magazine` WHERE `category_ID`={category_ID};"
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(result, columns=columns)
        data = df[["ID", "NAME", "Headline", "category_ID"]]
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
        return "https://retromagapi.azurewebsites.net/images" + result[0]
    return None

@app.route("/GetALLMagazine", methods=["GET"])
def get_all_magazine():
    try:
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
                    "NAME": row['NAME'],
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

                magazine_data = {
                "ID": str(five_df.loc[0]["ID"]),
                "NAME": five_df.loc[0]["NAME"],
                "Headline": five_df.loc[0]["Headline"],
                "ImageUrl": f"https://retromagapi.azurewebsites.net/images{image_df.loc[0]['image_url']}"
                }
                listofdata.append(magazine_data)

            processed_data = {"Model": result,"LatestFiveMagazines":listofdata}
            return jsonify(processed_data)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/GetDataMagazine", methods=["POST"])
def get_data_magazine():
    try:
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

        query2 = f"SELECT * FROM `image` WHERE `MAG_ID`={MAG_ID};"
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

        videos = [{"VideoUrl": "https://retromagapi.azurewebsites.net/images" + dt["video_url"]} for _, dt in df3.iterrows()]
        index["Videos"] = videos
        index["Headline"] = df0.loc[0].Headline

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
