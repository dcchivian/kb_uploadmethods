# -*- coding: utf-8 -*-
import os  # noqa: F401
import shutil
import time
import unittest
from configparser import ConfigParser
from os import environ

import requests
from biokbase.workspace.client import Workspace as workspaceService
from mock import patch

from installed_clients.DataFileUtilClient import DataFileUtil
from kb_uploadmethods.Utils.UploaderUtil import UploaderUtil
from kb_uploadmethods.authclient import KBaseAuth as _KBaseAuth
from kb_uploadmethods.kb_uploadmethodsImpl import kb_uploadmethods
from kb_uploadmethods.kb_uploadmethodsServer import MethodContext


class kb_uploadmethodsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token = environ.get('KB_AUTH_TOKEN', None)
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('kb_uploadmethods'):
            cls.cfg[nameval[0]] = nameval[1]
        authServiceUrl = cls.cfg.get('auth-service-url',
                                     "https://kbase.us/services/authorization/Sessions/Login")
        auth_client = _KBaseAuth(authServiceUrl)
        cls.user_id = auth_client.get_user(cls.token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': cls.token,
                        'user_id': cls.user_id,
                        'provenance': [
                            {'service': 'kb_uploadmethods',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.wsURL = cls.cfg['workspace-url']
        cls.wsClient = workspaceService(cls.wsURL, token=cls.token)
        cls.serviceImpl = kb_uploadmethods(cls.cfg)
        cls.dfu = DataFileUtil(os.environ['SDK_CALLBACK_URL'], token=cls.token)
        cls.scratch = cls.cfg['scratch']
        cls.shockURL = cls.cfg['shock-url']

        suffix = int(time.time() * 1000)
        cls.wsName = "test_kb_uploadmethods_attribute_mapping" + str(suffix)
        cls.wsID = cls.wsClient.create_workspace({'workspace': cls.wsName})[0]

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    @classmethod
    def delete_shock_node(cls, node_id):
        header = {'Authorization': 'Oauth {0}'.format(cls.token)}
        requests.delete(cls.shockURL + '/node/' + node_id, headers=header,
                        allow_redirects=True)
        print(('Deleted shock node ' + node_id))

    def getWsClient(self):
        return self.__class__.wsClient

    def getWsID(self):
        return self.__class__.wsID

    def getImpl(self):
        return self.__class__.serviceImpl

    def getContext(self):
        return self.__class__.ctx

    def mock_download_staging_file(params):
        print('Mocking DataFileUtilClient.download_staging_file')
        print(params)

        fq_filename = params.get('staging_file_subdir_path')
        fq_path = os.path.join('/kb/module/work/tmp', fq_filename)
        shutil.copy(os.path.join("data", fq_filename), fq_path)

        return {'copy_file_path': fq_path}

    def test_bad_import_attribute_mapping_from_staging_params(self):
        invalidate_input_params = {
          'missing_staging_file_subdir_path': 'staging_file_subdir_path',
          'workspace_name': 'workspace_name',
          'attribute_mapping_name': 'attribute_mapping_name',
        }
        with self.assertRaisesRegex(
                    ValueError,
                    '"staging_file_subdir_path" parameter is required, but missing'):
            self.getImpl().import_attribute_mapping_from_staging(self.getContext(),
                                                                 invalidate_input_params)

        invalidate_input_params = {
          'staging_file_subdir_path': 'staging_file_subdir_path',
          'missing_workspace_name': 'workspace_name',
          'attribute_mapping_name': 'attribute_mapping_name',
        }
        with self.assertRaisesRegex(
                    ValueError,
                    '"workspace_name" parameter is required, but missing'):
            self.getImpl().import_attribute_mapping_from_staging(self.getContext(),
                                                                 invalidate_input_params)

        invalidate_input_params = {
          'staging_file_subdir_path': 'staging_file_subdir_path',
          'workspace_name': 'workspace_name',
          'missing_attribute_mapping_name': 'attribute_mapping_name',
          'genome': 'genome'
        }
        with self.assertRaisesRegex(
                ValueError,
                '"attribute_mapping_name" parameter is required, but missing'):
            self.getImpl().import_attribute_mapping_from_staging(self.getContext(),
                                                                 invalidate_input_params)

    @patch.object(DataFileUtil, "download_staging_file", side_effect=mock_download_staging_file)
    @patch.object(UploaderUtil, "update_staging_service", return_value=None)
    def test_import_tsv_attribute_mapping_from_staging(self, download_staging_file,
                                                       update_staging_service):

        ws_obj_name = 'MyAttributeMapping'

        params = {'staging_file_subdir_path': "AM2.tsv",
                  'workspace_name': self.wsName,
                  'attribute_mapping_name': ws_obj_name,
                  }

        ref = self.getImpl().import_attribute_mapping_from_staging(self.getContext(), params)
        self.assertTrue('obj_ref' in ref[0])
        self.assertTrue('report_ref' in ref[0])
        self.assertTrue('report_name' in ref[0])

    @unittest.skip("should be tested in the parent module")
    @patch.object(DataFileUtil, "download_staging_file", side_effect=mock_download_staging_file)
    @patch.object(UploaderUtil, "update_staging_service", return_value=None)
    def test_import_excel_attribute_mapping_from_staging(self, download_staging_file,
                                                         update_staging_service):

        ws_obj_name = 'MyAttributeMapping'

        params = {'staging_file_subdir_path': "AM1.xlsx",
                  'workspace_name': self.wsName,
                  'attribute_mapping_name': ws_obj_name,
                  }

        ref = self.getImpl().import_attribute_mapping_from_staging(self.getContext(), params)
        self.assertTrue('obj_ref' in ref[0])
        self.assertTrue('report_ref' in ref[0])
        self.assertTrue('report_name' in ref[0])
