# programm app
import psycopg2
from psycopg2.extras import execute_values
from abc import ABC, abstractmethod
import json
import os
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="myapp.log",
    filemode="w",
)
print("Logging to:", os.path.abspath("myapp.log"))

logger = logging.getLogger(__name__)


class workDB:
    # currently no connection is created, it's settings for future connection
    def __init__(self):
        # function os.getenv read variable from environment from OS
        self.dsn = os.getenv("DATABASE_URL")
        self.conn = None

    # connect to DB
    def connect(self):
        # check connection
        if self.conn is None or self.conn.closed:
            try:
                self.conn = psycopg2.connect(self.dsn)
                print("DB connection is succsessfull!")
            except Exception as e:
                print(f"DB connection is failed: {e}")
                raise

    # create tables, indexes (no parameters are reqiered)
    def exec_no_param(self, query):
        try:
            # cursor will close automatically
            # withot WITH:
            # cursor = self.conn.cursor() cursor.execute() cursor.close()
            with self.conn.cursor() as cursor:
                cursor.execute(query)
                self.conn.commit()  # ?
                print("SQL run successfully!")
        except Exception as e:
            self.conn.rollback()
            print(f"SQL run with error: {e}")
            raise

    # bulk insertion in DB rooms (data as parameter)
    def insert(self, table_name, data):
        try:
            columns = data[0].keys()
            column_names = ", ".join(columns)
            query = f"INSERT INTO {table_name} ({column_names}) VALUES %s"
            # [(item["id"], item["name"]) for item in data] --> list of tuples
            values = [tuple(item[col] for col in columns) for item in data]
            lenght = len(values)
            with self.conn.cursor() as cur:
                # execute_values — bulk insertion
                execute_values(cur, query, values)
                self.conn.commit()  # ?
                print(f"Success! Table: {table_name}. Number of rows:{lenght}")
        except Exception as e:
            self.conn.rollback()
            print(f"ERROR. Rooms insertion FAILED: {e}")
            raise

    # select data
    def fetch_data(self, query):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query)
                # fetchall() take all records to python memory
                result = cursor.fetchall()
                print(f"Success! Number of rows were fetched: {len(result)}")
                return result
        except Exception as e:
            print(f"Error during select and fetch: {e}")
            raise

    # Close connection
    def close_conn(self):
        if self.conn:
            try:
                self.conn.close()
                print("DB connection is closed!")
            except Exception as e:
                print(f"Error while closing connection: {e}")


# Base Interface
class FileLoader(ABC):
    @abstractmethod  # decorator
    def load(self, file_path):
        pass


class JsonLoader(FileLoader):
    def load(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                print("Json was read successfully!")
                return json.load(f)  # list[dict]
        except Exception as e:
            print(f"Error during reading Json: {e}")
            raise


# Base Interface
class FileSaver(ABC):
    @abstractmethod
    def save(self, data, file_path):
        pass


# result files from data to app/data
class JsonSaver(FileSaver):
    def save(self, data, file_path):
        full_path = f"{file_path}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                # If you have a Python object, you can convert it into
                # a JSON string by using the json.dumps() method.
                # indent=4 for every key-value treir own row
                # ensure_ascii=False keeps all characters
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"Successfully saved results to {full_path}")
        except Exception as e:
            print(f"Failed to save file: {e}")
            raise


class XmlSaver(FileSaver):
    def save(self, data, file_path):
        full_path = f"{file_path}.xml"
        try:
            # Create the top-level container
            root = ET.Element("root")

            # Loop through your list of dictionaries
            for item in data:
                # Create a tag for each object
                row = ET.SubElement(root, "item")

                # Add each key-value pair as a nested tag
                for key, value in item.items():
                    # XML tags cannot have spaces,
                    # so we replace them just in case
                    tag_name = str(key).replace(" ", "_")
                    child = ET.SubElement(row, tag_name)
                    child.text = str(value)

            # Make it "Pretty" (with indents like JSON)
            xml_string = ET.tostring(root, encoding="utf-8")
            dom = minidom.parseString(xml_string)
            pretty_xml = dom.toprettyxml(indent="    ")

            # Write to file
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(pretty_xml)

            print(f"Successfully saved XML results to {full_path}")

        except Exception as e:
            print(f"Failed to save XML: {e}")
            raise


# here is all work combined
def main(room_path, student_path, output_type):
    logger.info("Started")
    try:
        logger.info("STEP 1 starting...")
        # object db of class workDB is created, init methon runs automatically
        db = workDB()
        db.connect()

        logger.info("STEP 2 starting...")
        # loading data from files
        LOADERS = {"json": JsonLoader()}  # <--- Creating an object here
        loader = LOADERS.get("json")

        rooms_data = loader.load(room_path)
        students_data = loader.load(student_path)

        logger.info("STEP 3 starting...")
        sql_create_rooms = """CREATE TABLE IF NOT EXISTS rooms(
                id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                name TEXT NOT NULL UNIQUE); """
        sql_create_students = """CREATE TABLE IF NOT EXISTS students(
                id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                birthday DATE,
                name TEXT NOT NULL,
                room INTEGER REFERENCES rooms(ID) ,
                sex CHAR(1)); """
        sql_index_room = (
            """CREATE INDEX IF NOT EXISTS idx_rooms_name ON rooms (name);"""
        )
        sql_index_fk_students = """CREATE INDEX IF NOT EXISTS
        idx_students_room_id ON students (room);"""

        db.exec_no_param(sql_create_rooms)  # create rooms
        db.exec_no_param(sql_create_students)  # create student
        db.exec_no_param(sql_index_fk_students)  # create index FK (students)
        db.exec_no_param(sql_index_room)  # create index room_name (rooms)

        logger.info("STEP 4 starting...")
        # insert data to DB
        table_name = "rooms"
        db.insert(table_name, rooms_data)
        table_name = "students"
        db.insert(table_name, students_data)

        logger.info("STEP 5 starting...")
        SAVERS = {"json": JsonSaver(), "xml": XmlSaver()}
        saver = SAVERS.get(output_type)
        if saver:
            print(f"Format {output_type} is supported")
        else:
            print(f"Format {output_type} is not supported. Json/Xml possible")
            raise

        # List of rooms and the number of students in each of them
        file_path = "results/roomsWithStudents"
        query = """SELECT
                        r.name room_name,
                        SUM(CASE WHEN s.id IS NOT NULL THEN 1 ELSE 0 END)
                        as count_student
                    FROM students s
                    RIGHT JOIN rooms r ON r.ID = s.room
                    GROUP BY r.name
                    ORDER BY r.name
                    ;"""
        raw_data = db.fetch_data(query)
        columns = ["room_name", "count_student"]
        data = [dict(zip(columns, row)) for row in raw_data]
        saver.save(data, file_path)

        # 5 rooms with the smallest average age of students
        file_path = "results/roomsWithSmallestAvgAge"
        query = """SELECT
                        r.name room_name
                    FROM rooms r
                    JOIN students s ON r.ID = s.room
                    GROUP BY r.name
                    ORDER BY AVG(EXTRACT(YEAR FROM AGE(s.birthday))) ASC
                    LIMIT 5
                    ;"""
        raw_data = db.fetch_data(query)
        columns = ["room_name"]
        data = [dict(zip(columns, row)) for row in raw_data]
        saver.save(data, file_path)

        # 5 rooms with the largest difference in the age of students
        file_path = "results/roomsWithLargestDiffAge"
        query = """SELECT
                        r.name room_name
                    FROM students s
                    JOIN rooms r ON r.ID = s.room
                    GROUP BY r.name
                    ORDER BY MAX(s.birthday) - MIN(s.birthday) DESC
                    LIMIT 5
                    ;"""
        raw_data = db.fetch_data(query)
        columns = ["room_name"]
        data = [dict(zip(columns, row)) for row in raw_data]
        saver.save(data, file_path)

        # List of rooms where different-sex students live
        file_path = "results/DiffSexStudents"
        query = """SELECT
                        r.name room_name
                    FROM rooms r
                    JOIN students s ON r.ID = s.room
                    GROUP BY r.name
                    HAVING COUNT(DISTINCT s.sex)>1
                    ORDER BY r.name
                    ;"""
        raw_data = db.fetch_data(query)
        columns = ["room_name"]
        data = [dict(zip(columns, row)) for row in raw_data]
        saver.save(data, file_path)

        sql_drop = """drop table students;
                drop table rooms;"""
        db.exec_no_param(sql_drop)

    finally:
        logger.info("STEP 6 starting...")
        db.close_conn()

    logger.info("Finished")


# build-in variable __name__.
# Next block of code runs only if I execute directly
# (in terminal or docker: python main.py)
if __name__ == "__main__":
    if len(sys.argv) < 4:
        logger.error(
            "Missing arguments! Required: <rooms_path> <students_path> <file_type>"
        )
        sys.exit(1)
    else:
        logger.info(
            "Starting with files: %s, %s, type: %s",
            sys.argv[1],
            sys.argv[2],
            sys.argv[3],
        )

    rooms_path = sys.argv[1]  # "/app/data/rooms.json"
    students_path = sys.argv[2]  # "/app/data/students.json"
    file_type = sys.argv[3]  # xml or json

    main(rooms_path, students_path, file_type)
