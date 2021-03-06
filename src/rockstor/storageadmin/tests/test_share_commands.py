"""
Copyright (c) 2012-2013 RockStor, Inc. <http://rockstor.com>
This file is part of RockStor.

RockStor is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published
by the Free Software Foundation; either version 2 of the License,
or (at your option) any later version.

RockStor is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase
import mock
from mock import patch
from storageadmin.tests.test_api import APITestMixin
from storageadmin.models import Share, Snapshot

class ShareCommandTests(APITestMixin, APITestCase):
    fixtures = ['fix1.json']
    BASE_URL = '/api/shares'

    @classmethod
    def setUpClass(cls):
        super(ShareCommandTests, cls).setUpClass()

        # post mocks
        cls.patch_update_quota = patch('storageadmin.views.share_command.update_quota')
        cls.mock_update_quota = cls.patch_update_quota.start()
        cls.mock_update_quota.return_value = 'foo'

        cls.patch_rollback_snap = patch('storageadmin.views.share_command.rollback_snap')
        cls.mock_rollback_snap = cls.patch_rollback_snap.start()
        cls.mock_rollback_snap.return_value = True

        cls.patch_create_clone = patch('storageadmin.views.share_command.create_clone')
        cls.mock_create_clone = cls.patch_create_clone.start()
        cls.mock_create_clone.return_value = Response('{"message": "ok!"}')


    @classmethod
    def tearDownClass(cls):
        super(ShareCommandTests, cls).tearDownClass()

    @mock.patch('storageadmin.views.share_command.Share')
    def test_clone_command(self, mock_share):

        """
        Test  invalid Post request
        1. Clone a share that does not exist
        2. Clone a share
        """
        # Clone a share that does not exist

        shareName = 'cshare1'
        data = {'name':'clone1'}

        # clone a share that does not exist
        mock_share.objects.get.side_effect = Share.DoesNotExist
        response = self.client.post('%s/%s/clone' % (self.BASE_URL, shareName), data=data)
        self.assertEqual(response.status_code,
                         status.HTTP_500_INTERNAL_SERVER_ERROR, msg=response.data)
        e_msg = ('Share(cshare1) does not exist')
        self.assertEqual(response.data['detail'], e_msg)
        conf = {'get.side_effect': None}
        mock_share.objects.configure_mock(**conf)

        # clone happy path
        data = {'name':'clone'}
        shareName = 'cshare2'
        response = self.client.post('%s/%s/clone' % (self.BASE_URL, shareName), data=data)
        self.assertEqual(response.status_code,
                         status.HTTP_200_OK, msg=response.data)


    @mock.patch('storageadmin.views.share_command.SambaShare')
    @mock.patch('storageadmin.views.share_command.NFSExport')
    @mock.patch('storageadmin.views.share_command.Snapshot')
    @mock.patch('storageadmin.views.share_command.Share')
    @mock.patch('storageadmin.views.share_command.Disk')
    def test_rollback_command(self, mock_disk, mock_share, mock_snapshot, mock_nfs, mock_samba):
        """
        1. Rollback share that does not exist
        2. Rollback share with no snapshot
        3. Rollback share while exported via NFS
        4. Rollback share while exported via Samba
        5. Rollback share
        """
        shareName = 'rshare2'
        data = {'name':'rsnap2'}

        # rollback share that does not exist
        mock_share.objects.get.side_effect = Share.DoesNotExist
        response = self.client.post('%s/%s/rollback' % (self.BASE_URL, shareName), data=data)
        self.assertEqual(response.status_code,
                         status.HTTP_500_INTERNAL_SERVER_ERROR, msg=response.data)
        e_msg = ('Share(rshare2) does not exist')
        self.assertEqual(response.data['detail'], e_msg)

        # rollback share snapshot does not exist
        class MockShare(object):
            def __init__(self, **kwargs):
                self.name = 'rshare2'

        mock_share.objects.get.side_effect = MockShare
        mock_snapshot.objects.get.side_effect = Snapshot.DoesNotExist
        response = self.client.post('%s/%s/rollback' % (self.BASE_URL, shareName), data=data)
        self.assertEqual(response.status_code,
                         status.HTTP_500_INTERNAL_SERVER_ERROR, msg=response.data)
        e_msg = ('Snapshot(rsnap2) does not exist for this Share(rshare2)')
        self.assertEqual(response.data['detail'], e_msg)
        mock_snapshot.objects.get.side_effect = None
        mock_share.objects.get.side_effect = None


        # rollback share while exported via NFS
        response = self.client.post('%s/%s/rollback' % (self.BASE_URL, shareName), data=data)
        self.assertEqual(response.status_code,
                         status.HTTP_500_INTERNAL_SERVER_ERROR, msg=response.data)
        e_msg = ('Share(rshare2) cannot be rolled back as it is exported via '
                 'nfs. Delete nfs exports and try again')
        self.assertEqual(response.data['detail'], e_msg)

        # rollback share while exported via Samba
        mock_nfs.objects.filter.return_value.exists.return_value = False
        response = self.client.post('%s/%s/rollback' % (self.BASE_URL, shareName), data=data)
        self.assertEqual(response.status_code,
                         status.HTTP_500_INTERNAL_SERVER_ERROR, msg=response.data)
        e_msg = ('Share(rshare2) cannot be rolled back as it is shared'
                 ' via Samba. Unshare and try again')
        self.assertEqual(response.data['detail'], e_msg)

        # rollback happy path
        mock_samba.objects.filter.return_value.exists.return_value = False
        r = self.client.post('%s/%s/rollback' % (self.BASE_URL, shareName), data=data)
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
