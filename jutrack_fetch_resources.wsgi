import os
import hashlib
import json

storage_folder = '/mnt/jutrack_data'
studies_folder = storage_folder + '/studies'
junk_folder = storage_folder + '/junk'
image_folder = storage_folder + '/image_resources'


# -----------------------------------------VALIDATION-----------------------------------------------
class JutrackError(Exception):
    """Base class for exceptions in this module."""
    pass


class JutrackValidationError(JutrackError):
    """Exception raised for unsuccessful validation of the json content.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


def is_valid_json(body, verbose):
    try:
        data = json.loads(body)
        if verbose:
            print("NOTICE: The uploaded content is valid json.")
    except Exception as e:
        raise JutrackValidationError("ERROR: The uploaded content is not valid json.")

    return data


def is_valid_study(study_id):
    if not os.path.isdir(studies_folder + "/" + study_id):
        raise JutrackValidationError(
            "Invalid study detected: " + str(study_id))


# compare MD5 values
def is_md5_matching(md5, calc_md5):
    if calc_md5 == md5:
        return True
    else:
        return False


# ----------------------------------------FETCH RESOURCE---------------------------------------------
def get_images(study_id):
    return image_folder + "/" + study_id + ".zip"

# ----------------------------------------APPLICATION------------------------------------------------


# This method is called by the main endpoint
def application(environ, start_response):
    output = {}
    file_path = ""
    file_name = ""
    status = "200 OK"
    # We only accept POST-requests
    if environ['REQUEST_METHOD'] == 'POST':
        # read request body
        try:
            request_body = environ['wsgi.input'].read()

            # read passed MD5 value
            if 'HTTP_MD5' in environ:
                md5 = environ['HTTP_MD5']
            else:
                md5 = environ['HTTP_CONTENT-MD5']

            # calc_md5 = hashlib.md5(request_body).hexdigest()
            calc_md5 = hashlib.md5()
            calc_md5.update(request_body)

            # Check MD5 and content. If both is good perform actions
            if is_md5_matching(md5, calc_md5.hexdigest()):
                try:
                    data = is_valid_json(request_body, 0)
                    study_id = data["study_id"]
                    file_name = study_id
                    is_valid_study(study_id)
                    file_path = get_images(study_id)
                except JutrackValidationError as e:
                    status = '409 Conflict'
                    output = {"message": e.message}

            else:
                print('expected MD5: ' + str(calc_md5.hexdigest()) + ', received MD5: ' + str(md5))
                status = '500 Internal Server Error: There has been an MD5-MISMATCH!'
                output = {"message": "MD5-MISMATCH: There has been a mismatch between the uploaded data and the received data, upload aborted!"}
        except ValueError:
            status = '500 Internal Server Error: ValueError occured during JSON parsing!'
            output = {"message": "The wsgi service was not able to parse the json content."}
    else:
        status = '500 Internal Server Error: Wrong request type!'
        output = {"message": "Expected POST-request!"}

    if file_path != "":
        fin = open(file_path, "rb")
        size = os.path.getsize(file_path)
        start_response("200 OK", [('Content-Type', 'application/zip'),
                                  ('Content-length', str(size)),
                                  ('Content-Disposition',
                                   'attachment; filename=' + file_name + '.zip')])  # return the entire file
        if 'wsgi.file_wrapper' in environ:
            return environ['wsgi.file_wrapper'](fin, 1024)
        else:
            return iter(lambda: fin.read(1024), '')
    else:
        start_response(status, [('Content-type', 'application/json')])
        output_dump = json.dumps(output)
        return [output_dump.encode('utf-8')]
