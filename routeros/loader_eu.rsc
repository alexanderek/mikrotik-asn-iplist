# RouterOS v7 loader for iplist resources (EU, PROD)

:local listName "blacklist_eu"

:global resources {
  "fastly";
  "googlecloud"
}

:if ([:len $resources] = 0) do={
  :log info "iplist[EU]: no resources configured"
  :return
}

:local baseUrl "https://raw.githubusercontent.com/alexanderek/MikroTik_ASN_IPList/main/dist"
:local minBytes 200

:log info ("iplist[EU]: start list=" . $listName . " resources=" . [:len $resources])

:foreach resource in=$resources do={

  :do {
    :log info ("iplist[EU]: fetching resource=" . $resource)

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

    :log info ("iplist[EU]: removing old entries resource=" . $resource)
    :local tag ("iplist:auto:" . $resource)

    :foreach i in=[/ip/firewall/address-list find] do={
      :if ([/ip/firewall/address-list get $i comment] = $tag) do={
        /ip/firewall/address-list remove $i
      }
    }

    :global AddressList $listName
    :log info ("iplist[EU]: importing resource=" . $resource)

    /import file-name=$tmpFile
    /file remove $tmpFile

    :log info ("iplist[EU]: loaded resource=" . $resource)

  } on-error={
    :log warning ("iplist[EU]: skipped resource=" . $resource)
  }
}

:log info "iplist[EU]: finished"
