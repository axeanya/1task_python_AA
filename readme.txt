Before run the app make sure:
- you have file .env with db credentials
- you don't have tables rooms and students with uploaded data. There are UNIQUE restrictions in DB
- you have folder results/ for storing downloaded json/xml results

Arguments are in docker compose file (rooms_path students_path file_type(xml or json))
command: python main.py Arg1 Arg2 Arg3

Input and output files are in Docker Volumes