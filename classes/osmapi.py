import requests


class OSM_API:
    def __init__(self):
        self.url = "https://overpass-api.de/api/interpreter"

    def query(self, query):
        """
        This function is used to query the overpass api
        """
        response = requests.get(self.url, params={"data": query})
        return response.json()

    def query_amenities(self, bbox):
        """
        This function is used to get the amenities within a bounding box
        """
        query = f"""
            [out:json];
            (
                nwr[shop][!leisure]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
                nwr[amenity][!leisure]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
                nwr[leisure][!amenity]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
                nwr[railway~"station"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
                nwr[sport][!shop][!amenity]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
                nwr[healthcare][!amenity]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
                nwr[craft][!amenity]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
                node[public_transport][!railway]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
                nwr[tourism~"gallery|theme_park|zoo|museum|aquarium"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
            );
            out geom;
        """
        return self.query(query)

    def query_buildings(self, bbox):
        query = f"""
            [out:json];
            (
                way[building]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
                relation[building]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
            );
            out geom;
        """
        return self.query(query)
