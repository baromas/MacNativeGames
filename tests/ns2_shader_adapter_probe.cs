using System;
using System.IO;
using System.Text.Json.Nodes;
using System.Reflection;

class RuntimeError : Exception { public RuntimeError(string s) : base(s) {} }
static partial class ShaderService {
    static string outDir = Environment.CurrentDirectory;
    static string GetStr(JsonObject o,string k,string fallback) => o[k]?.GetValue<string>() ?? fallback;
}
class Probe {
    static object Call(string name, params object[] args) => typeof(ShaderService).GetMethod(name,BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,args);
    static void Main(string[] args) {
        string s=Console.In.ReadToEnd();
        try {
            if(args[0]=="base")Console.Write(ShaderBaseInstance.Rewrite(s));
            else if(args[0]=="pool")Console.Write(ShaderPools.Rewrite(s));
            else {
                JsonObject rq=JsonNode.Parse(s).AsObject();
                if(args[0]=="prepare")Console.Write(((JsonObject)Call("PrepareMesh",rq)).ToJsonString());
                else Console.Write((string)Call("WrapMesh",(string)rq["source"],rq["info"].AsObject()));
            }
        } catch(Exception e) { Console.Error.WriteLine((e.InnerException??e).Message); Environment.Exit(1); }
    }
}
