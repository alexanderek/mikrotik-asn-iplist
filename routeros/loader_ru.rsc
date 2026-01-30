# RouterOS v7 loader for iplist resources (RU, PROD)

:local listName "blacklist_ru"

:global resources {
  "aws";
  "cloudflare";
  "hetzner"
}

:if ([:len $resources] = 0) do={
  :log info "iplist[RU]: no resources configured"
  :return
}

:local baseUrl "https://raw.githubusercontent.com/alexanderek/MikroTik_ASN_IPList/main/dist"
:local minBytes 200

:log info ("iplist[RU]: start list=" . $listName . " resources=" . [:len $resources])

:foreach resource in=$resources do={

  :do {
    :log info ("iplist[RU]: fetching resource=" . $resource)

    :local url ($baseUrl . "/" . $resource . ".rsc")
    :local tmpFile ("iplist_" . $resource . ".rsc.tmp")

    /tool fetch url=$url mode=https dst-path=$tmpFile keep-result=yes

    :if ([:len [/file find name=$tmpFile]] = 0) do={ :error "missing file" }

    :local size [/file get $tmpFile size]
    :if ($size < $minBytes) do={ :error "file too small" }

    :local contents [/file get $tmpFile contents]
    :if ([:find $contents "# iplist-rsc v1"] = nil) do={ :error "missing sentinel" }
    :if ([:find $contents ("# resource=" . $resource)] = nil) do={ :error "resource mismatch" }
    :if ([:find $contents ":global AddressList"] = nil) do={ :error "AddressList missing" }

    :log info ("iplist[RU]: removing old entries resource=" . $resource)
    :local tag ("iplist:auto:" . $resource)

    :foreach i in=[/ip/firewall/address-list find] do={
      :if ([/ip/firewall/address-list get $i comment] = $tag) do={
        /ip/firewall/address-list remove $i
      }
    }

    :global AddressList $listName
    :log info ("iplist[RU]: importing resource=" . $resource)

    /import file-name=$tmpFile
    /file remove $tmpFile

    :log info ("iplist[RU]: loaded resource=" . $resource)

  } on-error={
    :log warning ("iplist[RU]: skipped resource=" . $resource)
  }
}

:log info "iplist[RU]: finished"
