import os
import hashlib
import json
from PIL import Image
from io import BytesIO
import base64

storage_folder = '/mnt/jutrack_data'
studies_folder = storage_folder + '/studies'
junk_folder = storage_folder + '/junk'
resources_folder = storage_folder + '/image_resources'


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


def to_utf8(s):
    return s if isinstance(s, str) else s.decode('utf-8')


def to_bytes(s):
    return s if isinstance(s, bytes) else s.encode('utf-8')


# ----------------------------------------FETCH RESOURCE---------------------------------------------


def upload_image(data, filename, format):
    file = BytesIO(base64.b64decode(data))
    file_path = resources_folder+"/upload/image/"+filename
    pilimage = Image.open(file)
    pilimage.save(file_path, format)
    return "Image file "+file_path+" written to disc."


def upload_audio(data, filename):
    file = base64.b64decode(data)
    file_path = resources_folder+"/upload/audio/"+filename
    with open(file_path, mode='bx') as f:
        f.write(file)
    return "Audio file "+file_path+" written to disc."


def upload_zip(data, dest, filename, arch_type):
    file = base64.b64decode(data)
    if arch_type == "audio":
        if not os.path.isdir(resources_folder+"/upload/audio/"+dest):
            os.makedirs(resources_folder+"/upload/audio/"+dest)
        file_path = resources_folder+"/upload/audio/"+dest+filename
    else:
        if not os.path.isdir(resources_folder+"/upload/audio/"+dest):
            os.makedirs(resources_folder+"/upload/audio/"+dest)
        file_path = resources_folder + "/upload/image/" + dest + filename
    with open(file_path, mode='bw') as f:
        f.write(file)
    return "Zip archive "+file_path+" written to disc."


def upload_other(data, filename):
    file = base64.b64decode(data)
    file_path = resources_folder+"/upload/other/"+filename
    with open(file_path, mode='bx') as f:
        f.write(file)
    return "Other file "+file_path+" written to disc."


def download_image(filename):
    with open(resources_folder+"/download/image/"+filename+'.png', 'rb') as img:
        data = base64.b64encode(img.read())
    return data.decode("utf-8")


def download_audio(filename):
    with open(resources_folder+"/download/audio/"+filename, 'rb') as aud:
        data = base64.b64encode(aud.read())
    return data.decode("utf-8")


def download_zip(filename, arch_type):
    if arch_type == "audio":
        with open(resources_folder+"/download/audio/"+filename, 'rb') as my_zip:
            data = base64.b64encode(my_zip.read())
    else:
        with open(resources_folder+"/download/image/"+filename, 'rb') as my_zip:
            data = base64.b64encode(my_zip.read())
    return data.decode("utf-8")


def download_other(filename):
    with open(resources_folder+"/download/other/"+filename, 'rb') as my_file:
        data = base64.b64encode(my_file.read())
    return data.decode("utf-8")


# ----------------------------------------APPLICATION------------------------------------------------


# This method is called by the main endpoint
def application(environ, start_response):
    output = {}
    status = "200 OK"
    # We accept GET-requests to download files
    if environ['REQUEST_METHOD'] == 'GET':
        if 'HTTP_ACTION' in environ:
            action = environ['HTTP_ACTION']
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
                calc_md5.update(to_utf8(request_body).encode())

                # Check MD5 and content. If both is good perform actions
                #if is_md5_matching(md5, calc_md5.hexdigest()):
                try:
                    json_str = to_utf8(request_body)
                    json_text = '{"' + json_str.split('=')[0] + '": "' + json_str.split('=')[1]+'"}'
                    print(json_text)
                    data = is_valid_json(json_text, 0)

                    if "download_image" == action:
                        output = download_image(data['filename'])
                    elif "download_audio" == action:
                        output = download_audio(data['filename'])
                    elif "download_zip" == action:
                        arch_type = environ['HTTP_ARCHIVE']
                        output = download_zip(data['filename'], arch_type)
                    elif "download_other" == action:
                        output = download_other(data['filename'])
                    else:
                        status = '409 Conflict'
                        output = {"message": "Wrong action provided"}
                except JutrackValidationError as e:
                    status = '409 Conflict'
                    output = {"message": e.message}

                #else:
                print('expected MD5: ' + str(calc_md5.hexdigest()) + ', received MD5: ' + str(md5))
                    #status = '500 Internal Server Error: There has been an MD5-MISMATCH!'
                    #output = {
                    #    "message": "MD5-MISMATCH: There has been a mismatch between the uploaded data and the received data, upload aborted!"}
            except ValueError:
                status = '500 Internal Server Error: ValueError occured during JSON parsing!'
                output = {"message": "The wsgi service was not able to parse the json content."}
        else:
            status = '500 Internal Server Error: There has been a KEY MISSING!'
            output = {"message": "MISSING-KEY: There was no action-attribute defined, upload aborted!"}

        start_response(status, [('Content-type', 'application/json')])
        output_dump = json.dumps(output)
        return [output_dump.encode('utf-8')]

    # We accept POST-requests to upload files
    elif environ['REQUEST_METHOD'] == 'POST':
        if 'HTTP_ACTION' in environ:
            action = environ['HTTP_ACTION']
            # read request body
            try:
                request_body = environ['wsgi.input'].read()
                # get the passed MD5 value
                if 'HTTP_MD5' in environ:
                    md5 = environ['HTTP_MD5']
                else:
                    md5 = environ['HTTP_CONTENT-MD5']

                # calc_md5 = hashlib.md5(request_body).hexdigest()
                calc_md5 = hashlib.md5()
                calc_md5.update(request_body)

                # Check MD5 and content. If both is good perform actions
                #if is_md5_matching(md5, calc_md5.hexdigest()) or action == "upload_zip":
                try:
                    if action == "upload_images":
                        res = upload_image(request_body, environ['HTTP_FILENAME'], environ['HTTP_FORMAT'])
                    elif action == "upload_audio":
                        res = upload_audio(request_body, environ['HTTP_FILENAME'])
                    elif action == "upload_zip":
                        arch_type = environ['HTTP_ARCHIVE']
                        res = upload_zip(request_body, environ['HTTP_DEST'], environ['HTTP_FILENAME'], arch_type)
                    elif action == "upload_other":
                        res = upload_other(request_body, environ['HTTP_FILENAME'])
                    else:
                        res = "No valid action defined!"
                    print(res)
                    output = {"message": res}
                except JutrackValidationError as e:
                    status = '409 Conflict'
                    output = {"message": e.message}

                #else:
                print('expected MD5: ' + str(calc_md5.hexdigest()) + ', received MD5: ' + str(md5))
                    #status = '500 Internal Server Error: There has been an MD5-MISMATCH!'
                    #output = {
                    #    "message": "MD5-MISMATCH: There has been a mismatch between the uploaded data and the received data, upload aborted!"}
            except ValueError as e:
                print(e)
                status = '500 Internal Server Error: ValueError occured during JSON parsing!'
                output = {"message": "The wsgi service was not able to parse the json content."}
        else:
            status = '500 Internal Server Error: There has been a KEY MISSING!'
            output = {"message": "MISSING-KEY: There was no action-attribute defined, upload aborted!"}

        start_response(status, [('Content-type', 'application/json')])
        output_dump = json.dumps(output)
        return [output_dump.encode('utf-8')]
    else:
        status = '500 Internal Server Error: Wrong request type!'
        output = {"message": "Expected POST or GET Request!"}

        start_response(status, [('Content-type', 'application/json')])
        output_dump = json.dumps(output)
        return [output_dump.encode('utf-8')]
