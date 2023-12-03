import base64
import binascii
from zlib import decompress
from xml.dom import minidom


class PaReqUtils:
    def extract_xml(self, pareq_encode):
        try:
            xml_data = decompress(self._decode_pareq(pareq_encode))
            xml = minidom.parseString(xml_data)
            return xml.toprettyxml()

        except xml.parsers.expat.ExpatError as e:
            # You will get a xml.parsers.expat.ExpatError if the XML is
            # invalid.
            print(e)

    def _decode_pareq(self, pareq):
        try:
            return base64.b64decode(pareq)
        except binascii.Error as e:
            # A binascii.Error exception is raised if s is incorrectly padded.
            print(e)


pareq_chat = "18aff4c1-1227-4009-8a47-35f77e004afb"
pareq_chat = "eJxUku2OsjAQhW+F+HtDSwEVMzapaLJNxDXKZrM/mzJREkUt+Lq8V78tfi4JyZwzQ2d4ppBvDeJ0jfpskEOGda026JXFuMcGLKIhS2iPw1Ks8MThH5q6PFQ88KnPgNyl/czoraoaDkqfJnLB4yhg4RDITcIejZzyhL4+AZCrDZXaI8/lOhVz6S3Ftzf5mM9neS4XEkiXBH04V41peTikQO4CzmbHt01zHBFyuVz8Gnc75ZcNEJcA8hxreXZRbQ/6KQsuU7F5edvFf0mzadZ+5GIMxFVAoRrkjDJKYxZ5QX9E45GbuPNB7d0EfPa58qK3xE50M+Do+oiriFzi1QDL2GClW54MLJuHAvw5Hiq0FZbpI4YCa81FKiyp7Gud2N7OAPL8l/TdAdeNZViwmCV9OiwCrRiGASYYUlrY7QUDt4auyDUqLTfGaL/r5AQQdwy5bdgy626Ajf7cjF8AAAD//wXAgQAAAAAAkP9rAAKvsEA="
print(PaReqUtils().extract_xml(pareq_chat))
