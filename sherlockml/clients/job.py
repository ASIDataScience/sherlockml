# Copyright 2018 ASI Data Science
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

from collections import namedtuple

from marshmallow import Schema, fields, post_load

from sherlockml.clients.base import BaseClient

JobMetadata = namedtuple("JobMetadata", ["name", "description"])
JobIdAndMetadata = namedtuple("JobIdAndMetadata", ["id", "metadata"])


class JobMetadataSchema(Schema):
    name = fields.String(required=True)
    description = fields.String(required=True)

    @post_load
    def make_job_metadata(self, data):
        return JobMetadata(**data)


class JobIdAndMetadataSchema(Schema):
    id = fields.UUID(data_key="jobId", required=True)
    metadata = fields.Nested(JobMetadataSchema, data_key="meta", required=True)

    @post_load
    def make_job(self, data):
        return JobIdAndMetadata(**data)


class JobClient(BaseClient):

    SERVICE_NAME = "steve"

    def list(self, project_id):
        endpoint = "/project/{}/job".format(project_id)
        return self._get(endpoint, JobIdAndMetadataSchema(many=True))
