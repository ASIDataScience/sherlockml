# Copyright 2018-2019 Faculty Science Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import fnmatch
import os
import posixpath
import contextlib
import tempfile
import io

from faculty.session import get_session
from faculty.context import get_context
from faculty.clients.object import ObjectClient
from faculty.datasets import path, transfer
from faculty.datasets.session import DatasetsError


# For backwards compatibility
SherlockMLDatasetsError = DatasetsError


def ls(prefix="/", project_id=None, show_hidden=False, client=None):
    """List contents of project datasets.

    Parameters
    ----------
    prefix : str, optional
        List only files in the datasets matching this prefix. Default behaviour
        is to list all files.
    project_id : str, optional
        The project to list files from. You need to have access to this project
        for it to work. Defaults to the project set by FACULTY_PROJECT_ID in
        your environment.
    show_hidden : bool, optional
        Include hidden files in the output. Defaults to False.

    Returns
    -------
    list
        The list of files from the project datasets.
    """

    project_id = project_id or get_context().project_id
    client = client or ObjectClient(get_session())

    list_response = client.list(project_id, prefix)
    paths = [obj.path for obj in list_response.objects]

    while list_response.next_page_token is not None:
        list_response = client.list(
            project_id, prefix, list_response.next_page_token
        )
        paths += [obj.path for obj in list_response.objects]

    if show_hidden:
        return paths
    else:
        non_hidden_paths = [
            path
            for path in paths
            if not any(element.startswith(".") for element in path.split("/"))
        ]
        return non_hidden_paths


def glob(pattern, prefix="/", project_id=None, show_hidden=False):
    """List contents of project datasets that match a glob pattern.

    Parameters
    ----------
    pattern : str
        The pattern that contents need to match.
    prefix : str, optional
        List only files in the project datasets that have this prefix. Default
        behaviour is to list all files.
    project_id : str, optional
        The project to list files from. You need to have access to this project
        for it to work. Defaults to the project set by SHERLOCK_PROJECT_ID in
        your environment.
    show_hidden : bool, optional
        Include hidden files in the output. Defaults to False.

    Returns
    -------
    list
        The list of files from the project that match the glob pattern.
    """
    contents = ls(
        prefix=prefix, project_id=project_id, show_hidden=show_hidden
    )
    return fnmatch.filter(contents, pattern)


def _isdir(project_path, project_id=None, client=None):
    """Determine if a path in a project's datasets is a directory.

    Parameters
    ----------
    project_path : str
        The path in the project datasets to test.
    project_id : str, optional
        The project to list files from. You need to have access to this project
        for it to work. Defaults to the project set by FACULTY_PROJECT_ID in
        your environment.

    Returns
    -------
    bool
    """
    # 'Directories' always end in a '/' in S3
    if not project_path.endswith("/"):
        project_path += "/"
    matches = ls(
        project_path, project_id=project_id, show_hidden=True, client=client
    )
    return len(matches) >= 1


def _isfile(project_path, project_id=None, client=None):
    """Determine if a path in a project's datasets is a file.

    Parameters
    ----------
    project_path : str
        The path in the project directory to test.
    project_id : str, optional
        The project to list files from. You need to have access to this project
        for it to work. Defaults to the project set by FACULTY_PROJECT_ID in
        your environment.

    Returns
    -------
    bool
    """
    if _isdir(project_path, project_id):
        return False
    matches = ls(
        project_path, project_id=project_id, show_hidden=True, client=client
    )
    rationalised_path = path.rationalise_projectpath(project_path)
    return any(match == rationalised_path for match in matches)


def _create_parent_directories(project_path, project_id, s3_client):

    # Make sure empty objects exist for directories
    # List once for speed
    all_objects = set(ls("/", project_id=project_id, show_hidden=True))

    for dirname in path.project_parent_directories(project_path):

        if dirname == "/":
            # Root is not returned by ls
            continue

        # We're doing this manually instead of using _isdir as _isdir will
        # return true if '/somedir/myfile' exists, even if '/somedir/' does not
        if dirname not in all_objects:
            # Directories on S3 are empty objects with trailing '/' on the key
            client = ObjectClient(get_session())
            client.create_directory(project_id, dirname)


def _put_file(local_path, project_path, project_id):
    client = ObjectClient(get_session())
    transfer.upload(client, project_id, project_path, local_path)


def _put_directory(local_path, project_path, project_id, s3_client):
    client = ObjectClient(get_session())
    client.create_directory(project_id, project_path)

    # Recursively put the contents of the directory
    for entry in os.listdir(local_path):
        _put_recursive(
            os.path.join(local_path, entry),
            posixpath.join(project_path, entry),
            project_id,
            s3_client,
        )


def _put_recursive(local_path, project_path, project_id, s3_client):
    """Puts a file/directory without checking that parent directory exists."""
    if os.path.isdir(local_path):
        _put_directory(local_path, project_path, project_id, s3_client)
    else:
        _put_file(local_path, project_path, project_id)


def put(local_path, project_path, project_id=None):
    """Copy from the local filesystem to a project's datasets.

    Parameters
    ----------
    local_path : str or os.PathLike
        The source path in the local filesystem to copy.
    project_path : str
        The destination path in the project directory.
    project_id : str, optional
        The project to put files in. You need to have access to this project
        for it to work. Defaults to the project set by FACULTY_PROJECT_ID in
        your environment.
    """

    project_id = project_id or get_context().project_id
    if hasattr(os, "fspath"):
        local_path = os.fspath(local_path)

    s3_client = _s3_client(project_id)

    _create_parent_directories(project_path, project_id, s3_client)
    _put_recursive(local_path, project_path, project_id, s3_client)


def _get_file(project_path, local_path, project_id, client):

    if local_path.endswith("/"):
        msg = (
            "the source path {} is a normal file but the destination "
            "path {} indicates a directory - please provide a "
            "full destination path"
        ).format(repr(project_path), repr(local_path))
        raise DatasetsError(msg)

    transfer.download(client, project_id, project_path, local_path)


def _get_directory(project_path, local_path, project_id, client):

    # Firstly, make sure that the location to write to locally exists
    containing_dir = os.path.dirname(local_path)
    if not containing_dir:
        containing_dir = "."
    if not os.path.isdir(containing_dir):
        msg = "No such directory: {}".format(repr(containing_dir))
        raise IOError(msg)

    paths_to_get = ls(
        project_path, project_id=project_id, show_hidden=True, client=client
    )
    for object_path in paths_to_get:

        local_dest = os.path.join(
            local_path, path.project_relative_path(project_path, object_path)
        )

        if object_path.endswith("/"):
            # Objects with a trailing '/' on S3 indicate directories
            if not os.path.exists(local_dest):
                os.makedirs(local_dest)
        else:
            # Make sure directory exists to put files into
            dirname = os.path.dirname(local_dest)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            _get_file(object_path, local_dest, project_id)


def get(project_path, local_path, project_id=None):
    """Copy from a project's datasets to the local filesystem.

    Parameters
    ----------
    project_path : str
        The source path in the project datasets to copy.
    local_path : str or os.PathLike
        The destination path in the local filesystem.
    project_id : str, optional
        The project to get files from. You need to have access to this project
        for it to work. Defaults to the project set by FACULTY_PROJECT_ID in
        your environment.
    """

    project_id = project_id or get_context().project_id
    client = ObjectClient(get_session())

    if hasattr(os, "fspath"):
        local_path = os.fspath(local_path)

    if _isdir(project_path, project_id, client):
        _get_directory(project_path, local_path, project_id, client)
    else:
        _get_file(project_path, local_path, project_id, client)


def mv(source_path, destination_path, project_id=None, client=None):
    """Move a file within a project's datasets.

    Parameters
    ----------
    source_path : str
        The source path in the project datasets to move.
    destination_path : str
        The destination path in the project datasets.
    project_id : str, optional
        The project to get files from. You need to have access to this project
        for it to work. Defaults to the project set by FACULTY_PROJECT_ID in
        your environment.
    """

    project_id = project_id or get_context().project_id
    client = ObjectClient(get_session())

    cp(source_path, destination_path, project_id, client)
    rm(source_path, project_id, client)


def cp(
    source_path, destination_path, project_id=None, recursive=None, client=None
):
    """Copy a file within a project's datasets.

    Parameters
    ----------
    source_path : str
        The source path in the project datasets to copy.
    destination_path : str
        The destination path in the project datasets.
    project_id : str, optional
        The project to get files from. You need to have access to this project
        for it to work. Defaults to the project set by FACULTY_PROJECT_ID in
        your environment.
    recursive :
    client :
    """

    project_id = project_id or get_context().project_id
    client = ObjectClient(get_session())

    client.copy(project_id, source_path, destination_path, recursive=recursive)


def rm(project_path, project_id=None, recursive=None, client=None):
    """Remove a file from the project directory.

    Parameters
    ----------
    project_path : str
        The path in the project datasets to remove.
    project_id : str, optional
        The project to get files from. You need to have access to this project
        for it to work. Defaults to the project set by FACULTY_PROJECT_ID in
        your environment.
    recursive :
    client :
    """

    project_id = project_id or get_context().project_id
    client = ObjectClient(get_session())

    client.delete(project_id, project_path, recursive=recursive)


def rmdir(project_path, project_id=None, client=None):
    """Remove a directory from the project datasets.

    Parameters
    ----------
    remote_path : str
        The path of the directory to remove.
    project_id : str, optional
        The project to get files from. You need to have access to this project
        for it to work. Defaults to the project set by FACULTY_PROJECT_ID in
        your environment.
    client :
    """

    rm(project_path, project_id=project_id, recursive=True, client=client)


def etag(project_path, project_id=None, client=None):
    """Get a unique identifier for the current version of a file.

    Parameters
    ----------
    project_path : str
        The path in the project datasets.
    project_id : str, optional
        The project to get files from. You need to have access to this project
        for it to work. Defaults to the project set by FACULTY_PROJECT_ID in
        your environment.
    client :

    Returns
    -------
    str
    """

    project_id = project_id or get_context().project_id
    client = ObjectClient(get_session())

    object = client.get(project_id, project_path)

    return object.etag.strip('"')


@contextlib.contextmanager
def open(project_path, mode="r", temp_dir=None, **kwargs):
    """Open a file from a project's datasets for reading.

    This downloads the file into a temporary directory before opening it, so if
    your files are very large, this function can take a long time.

    Parameters
    ----------
    project_path : str
        The path of the file in the project's datasets to open.
    mode : str
        The opening mode, either 'r' or 'rb'. This is passed down to the
        standard python open function. Writing is currently not supported.
    temp_dir : str
        A directory on the local filesystem where you would like the file to be
        saved into temporarily. Note that on SherlockML servers, the default
        temporary directory can break with large files, so if your file is
        upwards of 2GB, it is recommended to specify temp_dir='/project'.
    """

    if _isdir(project_path):
        raise DatasetsError("Can't open directories.")

    if any(char in mode for char in ("w", "a", "x")):
        raise NotImplementedError("Currently, only reading is implemented.")

    tmpdir = tempfile.mkdtemp(prefix=".", dir=temp_dir)
    local_path = os.path.join(tmpdir, os.path.basename(project_path))

    try:
        get(project_path, local_path)
        with io.open(local_path, mode, **kwargs) as file_object:
            yield file_object
    finally:
        if os.path.isfile(local_path):
            os.remove(local_path)
        if os.path.isdir(tmpdir):
            os.rmdir(tmpdir)
