using System;
using System.Text.RegularExpressions;

// NVN2 byte/half-word stage stores can use Metal's native narrow stores.
// The named SPIR-V helper otherwise uses a CAS loop on the enclosing word,
// making lanes writing independent primitive indices contend unnecessarily.
// Adapted from seedds/nxnative ffebfd59 (MIT).
static class ShaderSharedStores
{
    static readonly Regex Helper = new(
        @"^void dmsh_shared_store(?<bits>8|16)_\d+\(thread const u?int& (?<off>\w+), thread const u?int& (?<val>\w+), " +
        @"(?<space>threadgroup|device) spvUnsafeArray<uint, \d+>& (?<mem>\w+)\)\n\{\n(?<body>.*?)^\}",
        RegexOptions.Multiline | RegexOptions.Singleline);

    internal static string Rewrite(string src)
    {
        const string metalNamespace = "using namespace metal;\n";
        if (!src.Contains("dmsh_shared_store", StringComparison.Ordinal)) return src;
        int aliasAt = src.IndexOf(metalNamespace, StringComparison.Ordinal);
        bool needsAlias = false;
        string result = Helper.Replace(src, m =>
        {
            Group body = m.Groups["body"];
            // Retain the generic helper when SPIRV-Cross changes its output.
            if (!body.Value.Contains("atomic_compare_exchange", StringComparison.Ordinal)) return m.Value;
            string index = $"uint({m.Groups["off"].Value})";
            string value = $"uint({m.Groups["val"].Value})";
            string space = m.Groups["space"].Value;
            string array = m.Groups["mem"].Value;
            bool half = m.Groups["bits"].Value == "16";
            if (half && aliasAt < 0) return m.Value;
            needsAlias |= half;
            string store = half
                ? $"(({space} dm_ushort_alias*)&{array}[0])[{index} >> 1u] = ushort({value});"
                : $"(({space} uchar*)&{array}[0])[{index}] = uchar({value});";
            return m.Value[..(body.Index - m.Index)] + "    " + store + "\n}";
        });
        // Both pointer types must alias the shared uint array. Metal's uchar
        // aliases naturally, while ushort needs the explicit alias attribute.
        return needsAlias
            ? result.Insert(aliasAt + metalNamespace.Length, "typedef ushort __attribute__((may_alias)) dm_ushort_alias;\n")
            : result;
    }
}
