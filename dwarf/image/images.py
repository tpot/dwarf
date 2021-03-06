#!/usr/bin/env python
#
# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
# Copyright (c) 2013 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import logging
import os

from hashlib import md5

from dwarf import config
from dwarf import utils

from dwarf.db import DB

CONF = config.Config()
LOG = logging.getLogger(__name__)

IMAGES_INFO = ('checksum', 'created_at', 'container_format', 'disk_format',
               'id', 'is_public', 'location', 'min_disk', 'min_ram', 'name',
               'owner', 'properties', 'protected', 'updated_at', 'size',
               'status')


class Controller(object):

    def list(self):
        """
        List all images
        """
        LOG.info('list()')

        images = DB.images.list()
        return utils.sanitize(images, IMAGES_INFO)

    def show(self, image_id):
        """
        Show image details
        """
        LOG.info('show(image_id=%s)', image_id)
        image = DB.images.show(id=image_id)
        return utils.sanitize(image, IMAGES_INFO)

    def create(self, image_fh, image_md):
        """
        Create a new image
        """
        LOG.info('create(image_md=%s)', image_md)

        # Create a new image in the database
        image_md['status'] = 'SAVING'
        image = DB.images.create(**image_md)
        image_id = image['id']

        # Copy the image and calculate its MD5 sum
        image_file = os.path.join(CONF.images_dir, image_id)
        with open(image_file, 'wb') as fh:
            d = md5()
            while True:
                buf = image_fh.read(4096)
                if not buf:
                    break
                d.update(buf)
                fh.write(buf)
        md5sum = d.hexdigest()

        # Update the image database entry
        image = DB.images.update(id=image_id, checksum=md5sum,
                                 location='file://%s' % image_file,
                                 status='ACTIVE')

        return utils.sanitize(image, IMAGES_INFO)

    def delete(self, image_id):
        """
        Delete an image
        """
        LOG.info('delete(image_id=%s)', image_id)

        # Delete the image in the database
        DB.images.delete(id=image_id)

        # Delete the image file
        image_file = os.path.join(CONF.images_dir, image_id)
        try:
            LOG.info('deleting image file %s', image_file)
            os.unlink(image_file)
        except OSError as ex:
            LOG.warn('failed to delete image %s (%s, %s)', image_file,
                     ex.errno, ex.strerror)

    def update(self, image_id, image_md):
        """
        Update image metadata
        """
        LOG.info('update(image_id=%s, image_md=%s)', image_id, image_md)

        image = DB.images.update(id=image_id, **image_md)
        return utils.sanitize(image, IMAGES_INFO)


IMAGES = Controller()
