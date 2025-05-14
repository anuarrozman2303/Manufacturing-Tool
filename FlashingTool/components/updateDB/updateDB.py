import mysql.connector
import logging
import os

logger = logging.getLogger(__name__)

script_dir = os.path.dirname(__file__)

class UpdateDB:
    
    def update_database(self, mac_address):
        try:
            connection = mysql.connector.connect(
                host="localhost",
                user="anuarrozman2303",
                password="Matter2303!",
                database="device_mac_sn"
            )

            cursor = connection.cursor()

            # Check if the MAC address already exists in the database
            cursor.execute("SELECT * FROM device_info WHERE mac_address = %s", (mac_address,))
            result = cursor.fetchone()

            if result:
                logger.debug(f"MAC address already exists in the database: {mac_address}")
            else:
                # Insert the MAC address into the database if it doesn't exist
                sql_query = """
                            UPDATE device_info SET mac_address = %s, status = 1
                            WHERE status = 0;
                            """
                cursor.execute(sql_query, (mac_address,))
                connection.commit()
                logger.info(f"MAC address inserted into the database: {mac_address}")

        except mysql.connector.Error as error:
            logger.error(f"Failed to update database: {error}")

        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                logger.info("MySQL connection closed.")

    def update_text_file(self, mac_address):
        # file_path = '/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt'
        # file_path = '/home/anuarrozman/Airdroitech/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt'
        file_path = str(script_dir) + "/../../device_data.txt"

        logger.error(f"starting update_text_file")
        try:
            with open(file_path, 'r+') as file:
                lines = file.readlines()
                updated_lines = []
                found = False

                for line in lines:
                    # if 'mac-address:' in line and 'Status:' in line and 'Status: 0' in line:
                    if 'mac-address:' in line:
                        line_parts = line.split(',')
                        # Assuming the order of parts and number of parts is fixed
                        for i, part in enumerate(line_parts):
                            if 'mac-address:' in part:
                                line_parts[i] = f" mac-address: {mac_address}"
                            # if 'Status:' in part:
                            #     line_parts[i] = " Status: 1\n"
                        # updated_line = ','.join(line_parts)
                        # updated_lines.append(updated_line)
                        found = True
                    else:
                        updated_lines.append(line)

                if not found:
                    raise IOError("No lines with Status: 0 found in the text file.")

                file.seek(0)
                file.writelines(updated_lines)
                file.truncate()

                logger.info(f"MAC address and status updated in the text file where status was 0: {mac_address}")
                print(f"MAC address and status updated in the text file where status was 0: {mac_address}")
        except IOError as e:
            logger.error(f"IOError occurred: {e}")
            print(f"IOError occurred: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            print(f"IOError occurred: {e}")
        except IOError as error:
            logger.error(f"Failed to update text file: {error}")
            print(f"Error: {error}")