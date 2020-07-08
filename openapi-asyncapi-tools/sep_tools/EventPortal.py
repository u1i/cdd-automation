import logging
import json
import re

import yaml
from .util import *

class EventPortal:
    spec = {}
    ApplicationDomains = {}
    Applications = {}
    Schemas = {}
    Events = {}
    
    _refSchemaRe = re.compile(r'\#\/components\/schemas/([^\/]+)$')
    _base_url = "https://solace.cloud"


    def __init__(self, token="", pubFlag=False, 
        admin_user="default", 
        admin_password="default", 
        host="", 
        vpn="default",
        queueName = "api_queue"):

        super().__init__()
        self.token = token
        self.pubFlag = pubFlag
        self.admin_user = admin_user
        self.admin_password = admin_password
        self.host = host
        self.vpn = vpn
        self.queueName = queueName

    def importOpenAPISpec(self, spec_path, domain, application):
        self.spec_path = spec_path
        self.domainName = domain
        self.appName = application
        self.ApplicationDomains[domain]={
            "payload":{
                "name": domain,
                "enforceUniqueTopicNames": True,
                "topicDomain": "",
            }
        }
        self.Applications[application]={
            "payload":{
                "name": application,
            }
        }
        
        with open(spec_path) as f:
            text_context = f.read()
            self.spec = yaml.safe_load(text_context)

        version = self.spec.get("openapi")
        if not version:
            logging.error("There is no 'openapi' filed in {}".format(spec_path))
            raise SystemExit

        if int(version.split(".")[0]) < 3:
            logging.error("The open api version of '{}' is {}, must be 3.x.".format(spec_path, version))
            raise SystemExit

        self.generate_ep_objects()
        self.check_existed_objects()
        self.create_all_objects()
        

    def generate_ep_objects(self):
        for path, path_item in self.spec["paths"].items():
            for method in HTTP_METHODS:
                if method not in path_item: continue
                operation = path_item.get(method)
                operationId = operation.get("operationId")
                event = {
                    "schemaName": None,
                    "payload": {
                        "name": operationId,
                        "description": operation.get("description", ""),
                        "topicName": method.upper()+path,
                    }
                }

                schemaName = self._extract_schema_from_operation(operation)
                if schemaName : event["schemaName"]=schemaName
                self.Events[operationId]=event
        
    def _extract_schema_from_operation(self, operation):
        schemaName = None
        content = operation.get("requestBody", {'content':{}}).get("content")
        jsonkeys = [k for k in content.keys() if k.startswith("application/json")]
        if len(jsonkeys) > 0:
            # only extract the first matched json schema
            schema = content.get(jsonkeys[0]).get("schema")
            if schema.get("$ref"):
                # Reference Object like #/components/schemas/CouponRequest
                schemaName = self._refSchemaRe.search(schema.get("$ref")).group(1)
                if not self.Schemas.get(schemaName): 
                    self.Schemas[schemaName]={
                        "id": None,
                        "payload": {
                            "contentType": "JSON",
                            "content": json.dumps(self._get_component_schema(schemaName)),
                            "name": schemaName,
                        }
                    }
            else:
                # Inline Schema Object
                schemaName = operation.get("operationId")+"_schema"
                self.Schemas[schemaName]={
                    "id": None,
                    "payload": {
                        "contentType": "JSON",
                        "content": json.dumps(schema),
                        "name": schemaName,
                    }
                }
        return schemaName

    def _get_component_schema(self, schemaName):
        payload = self.spec["components"]["schemas"][schemaName]
        self._dfs_ref_dict(payload)

        return payload

    def _dfs_ref_dict(self, payload):
        # Go through all reference object to combine an integrated schema
        # since Event Portal doesn't support reference insice schema
        for key, value in payload.items():
            if type(value) is dict:
                if value.get("$ref"):
                    # Reference Object
                    schemaName = self._refSchemaRe.search(value.get("$ref")).group(1)
                    payload[key] = self._get_component_schema(schemaName)
                else:
                    self._dfs_ref_dict(value)


    def check_existed_objects(self):
        to_check = {
            "applicationDomains": self.ApplicationDomains,
            "applications": self.Applications,
            "schemas": self.Schemas,
            "events": self.Events,
        }

        logging.info("Checking existed objects ...")
        isError = False
        applicationDomainId = None
        for coll_name, coll_objs in to_check.items():
            coll_url = self._base_url+"/api/v1/eventPortal/"+coll_name
            for obj_name, obj in coll_objs.items():
                print(".", end="", flush=True)
                url = coll_url+"?name="+obj_name
                rJson = rest("get", url, token=self.token)
                if len(rJson["data"]) > 0:
                    obj["id"] = rJson["data"][0]["id"]
                    obj["applicationDomainId"] = rJson["data"][0].get("applicationDomainId")
                    if coll_name == "applicationDomains":
                        applicationDomainId = obj["id"]
                    elif obj["applicationDomainId"] != applicationDomainId:
                        logging.error("{} '{}' already exists with another Application Domain[id:{}]".\
                            format(coll_name[:-1].capitalize(), obj_name, obj["applicationDomainId"]))
                        isError = True
                    else:
                        logging.warn("{} '{}' already exists".format(coll_name[:-1].capitalize(), obj_name))

        print()
        if isError: 
            raise SystemExit


    def create_all_objects(self):
        # 1. create application domain
        self._create_colls("applicationDomains", self.ApplicationDomains)
        applicationDomainId = self.ApplicationDomains[self.domainName]["id"]

        # 2. create application
        self.Applications[self.appName]["payload"]["applicationDomainId"] = applicationDomainId            
        self._create_colls("applications", self.Applications)
        applicationId = self.Applications[self.appName]["id"]

        # 3. create all schemas
        for s, v in self.Schemas.items():
            if not v.get("id"):
                v["payload"]["applicationDomainId"] = applicationDomainId
        self._create_colls("schemas", self.Schemas)

        # 4. create all events
        for e, v in self.Events.items():
            if not v.get("id"):
                event = v["payload"]
                event["applicationDomainId"] = applicationDomainId
#                event["consumedApplicationIds"] = [applicationId]
                if v["schemaName"] in self.Schemas:
                    event["schemaId"] = self.Schemas[v["schemaName"]]["id"]

        self._create_colls("events", self.Events)

        # 5. update the application to consume or publish all events
        eventIds = [ v["id"] for e, v in self.Events.items() ]
        data_json = { "producedEventIds" if self.pubFlag else "consumedEventIds": eventIds}
        
        url = self._base_url+"/api/v1/eventPortal/applications/"+applicationId
        rJson = rest("patch", url, data_json=data_json, token=self.token)
        logging.info("Events {} setting of Application '{}' on all events successfully.".\
            format('Published' if self.pubFlag else 'Subscribed', self.appName))


    def _create_colls(self, coll_name, coll_objs):
        # create objects of the same type
        coll_url = self._base_url+"/api/v1/eventPortal/"+coll_name
        for obj_name, obj_value in coll_objs.items():
            if obj_value.get("id"):
                # means this object has been existed
                continue
            # expected_code=201 Created.
            # The newly saved object is returned in the response body.
            rJson = rest("post", coll_url, data_json=obj_value["payload"],\
                expected_code=201, token=self.token)
            obj_value["id"] = rJson["data"]["id"]
            logging.info("{} '{}'[{}] created successfully".\
                format(coll_name[:-1].capitalize(), obj_name, obj_value["id"]))

# --------------------------- generate Queue ---------------------------
    def createQueue(self, spec_path):
        """Generate a queue based on the specified OpenAPI 3.0 specification by
        subscribing on all related events"""
        self.spec_path = spec_path
        
        with open(spec_path) as f:
            text_context = f.read()
            self.spec = yaml.safe_load(text_context)

        version = self.spec.get("openapi")
        if not version:
            logging.error("There is no 'openapi' filed in {}".format(spec_path))
            raise SystemExit

        if int(version.split(".")[0]) < 3:
            logging.error("The open api version of '{}' is {}, must be 3.x.".format(spec_path, version))
            raise SystemExit

        self.generate_ep_objects()
        self.__create_queue()
        self.__subscribe_on_events()

    def __create_queue(self):
        url = "{}/SEMP/v2/config/msgVpns/{}/queues".format(self.host, self.vpn)
        queue =  {
            "egressEnabled": True,
            "ingressEnabled": True,
            "permission": "consume",
            "queueName": self.queueName,
        }

        sempv2("post", url, self.admin_user, self.admin_password, queue)
        logging.info("Queue '{}' created successfully".format(self.queueName))

        pass

    def __subscribe_on_events(self):
        url = "{}/SEMP/v2/config/msgVpns/{}/queues/{}/subscriptions".\
            format(self.host, self.vpn, self.queueName)

        para = re.compile("{[^}]+}")
        for e, v in self.Events.items():
            topic = para.sub("*", v["payload"]["topicName"])
            sub = {"subscriptionTopic":topic}
            sempv2("post", url, self.admin_user, self.admin_password, sub)
            logging.info("Queue '{}' subscribed on '{}' successfully".\
                format(self.queueName, topic))

# --------------------------- generate AsyncApi ---------------------------

    def generateAsyncApi(self, application_name):
        # 1. get application id by name
        app_id = self._getObjectIdByName("applications", application_name)
        if not app_id:
            logging.error("Could not find Application '{}'!".format(application_name))
            raise SystemExit

        # 2. generate AsyncApi
        gen_url = self._base_url+\
            "/api/v1/eventPortal/applications/{}/generateAsyncApiRequest".format(app_id)
        request = {
            "asyncApiVersion": "2.0.0",
        }
        rJson = rest("post", gen_url, request, token=self.token)
        print(json.dumps(rJson,indent=2))


# --------------------------- generate OpenApi ---------------------------

    def generateOpenApi(self, domain_name):
        # 1. get the domain id by name
        domain_obj = self._getObjectByName("applicationDomains", domain_name)        
        if not domain_obj:
            logging.error("Could not find Application Domain '{}'!".format(domain_name))
            raise SystemExit
        else:
            domain_id = domain_obj["id"]
        
        # 2. get all events in the given application domain
        query_dict = {"applicationDomainId": domain_id}
        event_list = self._getAllObjects("events", query_dict)

        # 3. filter external events
        event_list = [e for e in event_list if \
            len(e["consumedApplicationIds"])>0]
#            len(e["producedApplicationIds"])==0 and len(e["consumedApplicationIds"])>0]

        # 4. get all related schemas
        schema_IDs = set([e["schemaId"] for e in event_list if e["schemaId"]])
        query_dict = {
            "ids": ",".join(list(schema_IDs)),
        }
        schema_list = self._getAllObjects("schemas", query_dict)

        # 5. generate openapi spec
        generateOpenAPISpec(domain_name, domain_obj["description"], event_list, schema_list)


# --------------------------- helper methods ---------------------------

    def _getObjectByName(self, coll, name):
        coll_url = "{}/api/v1/eventPortal/{}?name={}".format(
            self._base_url, coll, name
        )
        rJson = rest("get", coll_url, token=self.token)
        if len(rJson["data"]) == 0:
            return None
        else:
            return rJson["data"][0]

    def _getObjectIdByName(self, coll, name):
        obj = self._getObjectByName(coll, name)
        return obj["id"] if obj else None

    def _getAllObjects(self, coll, query_dict):
        params = {
            "pageSize": 100,
            "pageNumber": 1
        }
        params.update(query_dict)

        data_list = []
        while params["pageNumber"]:
            get_url = "{}/api/v1/eventPortal/{}".format(
                self._base_url, coll
            )
            rJson = rest("get", get_url, params=params, token=self.token)
            data_list.extend(rJson['data'])

            pagination = safeget(rJson, "meta", "pagination")
            params["pageNumber"]=pagination["nextPage"]
        
        return data_list